# -*- coding: utf-8 -*-
"""
실장석 공원 제국 - 전투 엔진 (battle_engine.py)
[v0.3.0] 침공/방어 전투 시뮬레이션.
  - 출정 유닛 선택 (경호/성체 각 인원 지정)
  - 보스실장 참전 옵션 (전투력 대폭↑, 패배 시 보스 HP↓)

전투 흐름:
1. 공격자/방어자 전투력 계산 (출정 유닛 기반)
2. 랜덤 요소 가미한 승패 판정
3. 피해 계산 (양측 사상자 - 출정 유닛에서만)
4. 승리 시 약탈 (자원 + 인구 포획)
5. 보스 참전 시 패배하면 보스 HP 감소
6. 전투 로그 + 대사 기록
"""
import random
import json
import math

from sqlalchemy import case

from app.models import db, Park, BattleLog, EventLog
from app.config import GameConfig as GC
from app import dialogues as DLG
from app.game_engine import add_event


def execute_battle(attacker, defender, send_guards=None, send_adults=None, boss_joins=False):
    """
    전투 실행.
    매개변수:
      - send_guards: 출정 경호실장 수 (None이면 방어 배치 제외 전원)
      - send_adults: 출정 성체실장 수 (None이면 방어 배치 제외 전원)
      - boss_joins: 보스실장 참전 여부
    반환: (승리여부, 전투로그 딕셔너리, 대사 리스트)
    """
    messages = []

    # [v1.7.0] 비관적 락(Pessimistic Lock): 동시 약탈 Race Condition 방지 (audit_report_14.md [IMP-F037])
    # [v1.7.0] Deadlock 방지: id 오름차순으로 락 획득 (audit_report_21.md [DEADLOCK-F001])
    lock_ids = sorted([attacker.id, defender.id])
    Park.query.filter(Park.id.in_(lock_ids)).with_for_update().all()
    db.session.refresh(attacker)
    db.session.refresh(defender)

    # [v1.8.3] 비관적 락 획득 후 양측 멸망 상태 재검증 (Zombie State TOCTOU 방지)
    if attacker.is_destroyed or defender.is_destroyed:
        return False, {'konpeito': 0, 'trash': 0, 'material': 0, 'babies': 0, 'children': 0}, \
            ["이미 멸망한 공원과는 전투를 치를 수 없는 데스!"]

    # === 0. 출정 인원 결정 ===
    # 방어 배치 인원을 제외한 가용 인원 [v1.7.0] 보유량 초과 방지 (audit_report_8.md [IMP-F017])
    avail_guards = max(0, min(attacker.guard_count, attacker.guard_count - attacker.defending_guards))
    avail_adults = max(0, min(attacker.adult_count, attacker.adult_count - attacker.defending_adults))

    # 출정 수 결정 (지정값이 없으면 전원, 가용 인원 초과 불가)
    if send_guards is None:
        send_guards = avail_guards
    else:
        send_guards = max(0, min(send_guards, avail_guards))

    if send_adults is None:
        send_adults = avail_adults
    else:
        send_adults = max(0, min(send_adults, avail_adults))

    # 최소 1명은 보내야 함
    if send_guards + send_adults == 0 and not boss_joins:
        return False, {'konpeito': 0, 'trash': 0, 'material': 0, 'babies': 0, 'children': 0}, \
            ["아무도 안 보내면 침공할 수 없는 데스!"]

    # === 1. 전투력 계산 ===
    atk_power = _calc_attack_power_selected(send_guards, send_adults, attacker.morale, boss_joins)
    def_power = _calc_defense_power(defender)

    # 랜덤 요소 (±20% 변동)
    atk_roll = atk_power * random.uniform(0.8, 1.2)
    def_roll = def_power * random.uniform(0.8, 1.2)

    # === 2. 승패 판정 ===
    attacker_wins = atk_roll > def_roll
    power_ratio = atk_roll / max(def_roll, 1)

    # 출발 대사
    if boss_joins:
        messages.append("👑 보스실장이 직접 출전하는 데스!! 전투력이 폭발적인 데스!!")
    if send_guards > 0:
        messages.append(DLG.get_random_dialogue(DLG.BATTLE_DEPART['guard']))
    elif send_adults > 0:
        messages.append(DLG.get_random_dialogue(DLG.BATTLE_DEPART['adult']))

    # === 3. 피해 계산 (출정 유닛에서만) ===
    atk_losses = _calc_losses_selected(send_guards, send_adults, power_ratio, is_winner=attacker_wins)
    def_losses = _calc_losses(defender, 1 / power_ratio, is_attacker=False)

    # 피해 적용
    # [v1.7.0] 공격자 피해도 원자적 UPDATE로 처리: refresh 시 덮어쓰기 방지 (audit_report_14.md [IMP-F035])
    Park.query.filter(Park.id == attacker.id).update({
        'guard_count': case((Park.guard_count < atk_losses.get('guards', 0), 0), else_=Park.guard_count - atk_losses.get('guards', 0)),
        'adult_count': case((Park.adult_count < atk_losses.get('adults', 0), 0), else_=Park.adult_count - atk_losses.get('adults', 0)),
    })
    _apply_losses(defender, def_losses)
    # [v1.7.0] 공격자/방어자 메모리 동기화: 원자적 UPDATE 반영 후 인구 공간 정확 계산 (audit_report_12.md [IMP-F029])
    db.session.refresh(attacker)
    db.session.refresh(defender)

    # === 4. 약탈 (공격자 승리 시) ===
    loot = {'konpeito': 0, 'trash': 0, 'material': 0, 'babies': 0, 'children': 0}

    if attacker_wins:
        loot = _calculate_loot(defender)
        # [v1.7.0] 적대 보너스: 적대 관계면 약탈 +20%
        # 플레이어와 NPC 모두에게 공평하게 적용 (audit_report_31.md [LOGIC-F005])
        from app.models import Diplomacy
        is_enemy = Diplomacy.query.filter(
            ((Diplomacy.park_a_id == attacker.id) & (Diplomacy.park_b_id == defender.id)) |
            ((Diplomacy.park_a_id == defender.id) & (Diplomacy.park_b_id == attacker.id)),
            Diplomacy.relation_type == 'enemy',
            Diplomacy.status == 'active'
        ).first()
        if is_enemy:
            loot['konpeito'] = int(loot['konpeito'] * 1.2)
            loot['trash'] = int(loot['trash'] * 1.2)
            loot['material'] = int(loot['material'] * 1.2)
            messages.append('⚔️ 적대 보너스! 약탈량 +20%!')
        _apply_loot(attacker, defender, loot)

        # 승리 대사
        messages.extend(DLG.get_random_dialogues(DLG.BATTLE_WIN, 2))
        if loot['children'] > 0:
            messages.append(DLG.get_random_dialogue(DLG.BATTLE_WIN_CAPTURED_CHILD))

        # 승리 시 사기 상승 [v1.7.0] 방어자 원자적 UPDATE (audit_report_10.md [IMP-F022])
        attacker.morale = min(100, attacker.morale + 8)
        Park.query.filter(Park.id == defender.id).update({
            'morale': Park.morale - 12,
        })
    else:
        # 패배 대사
        messages.extend(DLG.get_random_dialogues(DLG.BATTLE_LOSE, 2))

        # 패배 시 사기 변동 [v1.7.0] 방어자 원자적 UPDATE
        attacker.morale = max(0, attacker.morale - 8)
        Park.query.filter(Park.id == defender.id).update({
            'morale': Park.morale + 5,
        })

    # === 5. 보스 피해 판정 ===
    # [v1.5.1] 보스 단독 출전 시 승리해도 소량 HP 감소 (무손실 파밍 Exploit 차단)
    boss_solo = boss_joins and (send_guards + send_adults == 0)
    if boss_joins and not attacker_wins:
        # 보스가 참전했는데 졌으면 확정 피해
        boss_dmg = random.randint(10, 25)
        attacker.boss_hp = max(0, attacker.boss_hp - boss_dmg)
        messages.append(f"👑 보스실장이 전투에서 {boss_dmg} 피해를 입은 데스!!")
        if attacker.boss_hp <= 0:
            attacker.is_destroyed = True
            messages.append("💀 보스실장이 죽었는 데스... 공원은 멸망한 데스...")
    elif boss_solo and attacker_wins:
        # [v1.5.1] 보스 단독 승리: 호위 없이 전투하므로 경미한 피해 (3~8)
        boss_dmg = random.randint(3, 8)
        attacker.boss_hp = max(0, attacker.boss_hp - boss_dmg)
        messages.append(f"👑 호위 없이 싸워서 보스실장이 {boss_dmg} 피해를 입은 데스!")
        if attacker.boss_hp <= 0:
            attacker.is_destroyed = True
            messages.append("💀 무모한 단독 출전... 보스실장이 쓰러진 데스...")
    elif not attacker_wins and power_ratio < 0.3:
        # 보스 미참전이라도 대패 시 소량 피해
        boss_dmg = random.randint(3, 10)
        attacker.boss_hp = max(0, attacker.boss_hp - boss_dmg)
        messages.append(f"👑 대패! 보스실장이 간접 피해 {boss_dmg}를 입은 데스!")
        if attacker.boss_hp <= 0:
            attacker.is_destroyed = True
            messages.append("💀 보스실장이 죽었는 데스... 공원은 멸망한 데스...")

    # 방어자 보스 피해 (대승 시) [v1.7.0] 원자적 UPDATE (audit_report_10.md [IMP-F022])
    if attacker_wins and power_ratio > 2.0:
        boss_dmg = random.randint(5, 15)
        Park.query.filter(Park.id == defender.id).update({
            'boss_hp': Park.boss_hp - boss_dmg,
        })
        # [v1.7.0] 방어자 boss_hp가 0 이하로 떨어지면 즉시 멸망 처리
        # process_turn의 글로벌 검증에 의존하지 않고 바로 반영 (audit_report_34.md [STATE-F009])
        db.session.refresh(defender)
        if defender.boss_hp <= 0:
            defender.is_destroyed = True
            messages.append(f"💀 {defender.name}의 보스실장이 쓰러졌는 데스... 공원 멸망!")

    # === 6. 전투 로그 저장 ===
    result_text = 'win' if attacker_wins else 'lose'
    log_text = _format_battle_log(attacker, defender, attacker_wins,
                                   atk_losses, def_losses, loot,
                                   send_guards, send_adults, boss_joins)

    battle_log = BattleLog(
        attacker_id=attacker.id,
        defender_id=defender.id,
        result=result_text,
        log_text=log_text,
        loot_konpeito=loot['konpeito'],
        loot_trash=loot['trash'],
        loot_material=loot['material'],
        loot_babies=loot['babies'],
        loot_children=loot['children'],
        attacker_losses=json.dumps(atk_losses),
        defender_losses=json.dumps(def_losses),
    )
    db.session.add(battle_log)

    # 이벤트 로그 (양측)
    boss_tag = " (👑보스 출전)" if boss_joins else ""
    if attacker_wins:
        add_event(attacker, 'battle',
                  f"⚔️ {defender.name} 침공 승리!{boss_tag} "
                  f"🍬{loot['konpeito']} 🗑️{loot['trash']} "
                  f"🧱{loot['material']} 🐛{loot['babies']} 👶{loot['children']} 약탈!")
        add_event(defender, 'battle',
                  f"⚔️ {attacker.name}의 침공을 당했는 데스! 자원을 빼앗겼는 데스!!")
    else:
        add_event(attacker, 'battle',
                  f"⚔️ {defender.name} 침공 실패...{boss_tag} 피해를 입은 데스...")
        add_event(defender, 'battle',
                  f"⚔️ {attacker.name}의 침공을 막아냈는 데스!! "
                  + DLG.get_random_dialogue(DLG.BATTLE_DEFEND_WIN))

    # [v1.7.0] commit은 호출자(attack 라우트 또는 NPC 엔진)에서 처리 (audit_report_10.md [IMP-F022])
    return attacker_wins, loot, messages


def _calc_attack_power_selected(send_guards, send_adults, morale, boss_joins):
    """출정 유닛 기반 공격력 계산"""
    base = (send_guards * GC.POWER_GUARD +
            send_adults * GC.POWER_ADULT)

    # 보스 참전 보너스
    if boss_joins:
        base += GC.POWER_BOSS
        # [v1.5.1] 보스 단독 출전 패널티: 호위 없이 싸우면 전투력 30% 감소
        if send_guards + send_adults == 0:
            base = int(base * 0.7)

    # 사기 보정
    morale_mult = 1.0 + (morale - 50) * GC.MORALE_COMBAT_EFFECT / 50
    return max(1, int(base * morale_mult))


def _calc_defense_power(park):
    """방어자 전투력 (방어 배치 인원 + 방벽/감시탑/사기 보너스) [v1.7.0]"""
    # [v1.7.0] spec.md 9.9/12.1 기준: 방어력은 방어 배치 인원(defending_*)만 기준으로 계산
    base = (park.defending_guards * GC.POWER_GUARD +
            park.defending_adults * GC.POWER_ADULT)

    # 방벽 보너스 (개당 20%)
    wall_bonus = 1.0 + park.walls * 0.2
    # 감시탑 보너스 (기습 방지 = 10%)
    tower_bonus = 1.0 + (0.1 if park.watchtowers > 0 else 0)

    morale_mult = 1.0 + (park.morale - 50) * GC.MORALE_COMBAT_EFFECT / 50
    return max(1, int(base * wall_bonus * tower_bonus * morale_mult))


def _stochastic_round(value):
    """[v1.7.0] 확률적 반올림: 소수부를 확률로 처리하여 int 절사 Exploit 방지 (audit_report_6.md [IMP-F008])"""
    base = int(value)
    frac = value - base
    if frac > 0 and random.random() < frac:
        base += 1
    return base


def _calc_losses_selected(send_guards, send_adults, power_ratio, is_winner):
    """출정 유닛에서의 피해 계산"""
    losses = {'guards': 0, 'adults': 0, 'children': 0}

    if is_winner:
        loss_rate = random.uniform(0.05, 0.2)   # 승자: 5~20% 손실
    else:
        loss_rate = random.uniform(0.2, 0.5)     # 패자: 20~50% 손실

    raw_guard_loss = send_guards * loss_rate
    raw_adult_loss = send_adults * loss_rate

    losses['guards'] = min(send_guards, max(0, _stochastic_round(raw_guard_loss)))
    losses['adults'] = min(send_adults, max(0, _stochastic_round(raw_adult_loss)))

    return losses


def _calc_losses(park, power_ratio, is_attacker):
    """
    전투 피해 계산 (방어자용). power_ratio가 높을수록 피해가 적음.
    [v1.7.0] stochastic_round 적용 (audit_report_6.md [IMP-F008])
    반환: {'guards': n, 'adults': n, 'children': n}
    """
    losses = {'guards': 0, 'adults': 0, 'children': 0}

    # 패배 시 피해가 더 큼
    if power_ratio < 1:
        loss_rate = random.uniform(0.2, 0.5)  # 패자: 20~50% 손실
    else:
        loss_rate = random.uniform(0.05, 0.2)  # 승자: 5~20% 손실

    losses['guards'] = min(park.guard_count, _stochastic_round(park.guard_count * loss_rate))
    losses['adults'] = min(park.adult_count, _stochastic_round(park.adult_count * loss_rate))
    losses['children'] = min(park.child_count, _stochastic_round(park.child_count * loss_rate * 0.5))

    return losses


def _apply_losses(park, losses):
    """전투 피해를 공원에 적용 [v1.7.0] 원자적 UPDATE + 음수 방지 case() (audit_report_11.md [IMP-F027])
    [v1.7.0] 방어 배치 인원 동기화: guard_count/adult_count 차감 시 defending_guards/defending_adults도
    함께 clamping하여 다중 피격 시 좀비 방어 병력 방지 (audit_report_30.md [STATE-F005])"""
    Park.query.filter(Park.id == park.id).update({
        'guard_count': case((Park.guard_count < losses.get('guards', 0), 0), else_=Park.guard_count - losses.get('guards', 0)),
        'adult_count': case((Park.adult_count < losses.get('adults', 0), 0), else_=Park.adult_count - losses.get('adults', 0)),
        'child_count': case((Park.child_count < losses.get('children', 0), 0), else_=Park.child_count - losses.get('children', 0)),
        # [v1.7.0] 방어 배치 인원도 실제 병력 감소에 맞춰 clamping (audit_report_30.md [STATE-F005])
        'defending_guards': case(
            (Park.guard_count < losses.get('guards', 0), 0),
            (Park.defending_guards > Park.guard_count - losses.get('guards', 0), Park.guard_count - losses.get('guards', 0)),
            else_=Park.defending_guards
        ),
        'defending_adults': case(
            (Park.adult_count < losses.get('adults', 0), 0),
            (Park.defending_adults > Park.adult_count - losses.get('adults', 0), Park.adult_count - losses.get('adults', 0)),
            else_=Park.defending_adults
        ),
    })


def _calculate_loot(defender):
    """약탈량 계산 (spec.md 기준 비율)"""
    loot = {
        'konpeito': int(defender.konpeito * random.uniform(*GC.LOOT_KONPEITO_RATIO)),
        'trash': int(defender.trash_food * random.uniform(*GC.LOOT_TRASH_RATIO)),
        'material': int(defender.material * random.uniform(*GC.LOOT_MATERIAL_RATIO)),
        'babies': int(defender.baby_count * random.uniform(*GC.LOOT_BABY_RATIO)),
        'children': int(defender.child_count * random.uniform(*GC.LOOT_CHILD_RATIO)),
    }
    return loot


def _apply_loot(attacker, defender, loot):
    """약탈 적용: 방어자에서 빼고 공격자에 더함 [v1.7.0] 양측 모두 원자적 UPDATE + case() (audit_report_12.md [IMP-F029])"""
    # 방어자에서 차감 — 원자적 UPDATE로 동시 공격 Race Condition 방지, case()로 음수 방지
    Park.query.filter(Park.id == defender.id).update({
        'konpeito': case((Park.konpeito < loot['konpeito'], 0), else_=Park.konpeito - loot['konpeito']),
        'trash_food': case((Park.trash_food < loot['trash'], 0), else_=Park.trash_food - loot['trash']),
        'material': case((Park.material < loot['material'], 0), else_=Park.material - loot['material']),
        'baby_count': case((Park.baby_count < loot['babies'], 0), else_=Park.baby_count - loot['babies']),
        'child_count': case((Park.child_count < loot['children'], 0), else_=Park.child_count - loot['children']),
    })

    # [v1.7.0] 공격자 메모리 동기화: 원자적 UPDATE 반영 후 인구 공간 정확 계산 (audit_report_12.md [IMP-F029])
    db.session.refresh(attacker)
    space = max(0, attacker.population_cap - attacker.total_population)
    max_child = attacker.child_count + space

    # 공격자에게 추가 — 원자적 UPDATE + case() 캡핑 (메모리 덮어쓰기 방지)
    # [v1.7.0] baby_cap hybrid_property 사용: 운치굴 0개일 때도 최소 5마리 보장 (audit_report_32.md [STATE-F007])
    Park.query.filter(Park.id == attacker.id).update({
        'konpeito': case((Park.konpeito + loot['konpeito'] > Park.konpeito_cap, Park.konpeito_cap), else_=Park.konpeito + loot['konpeito']),
        'trash_food': case((Park.trash_food + loot['trash'] > Park.trash_food_cap, Park.trash_food_cap), else_=Park.trash_food + loot['trash']),
        'material': case((Park.material + loot['material'] > Park.material_cap, Park.material_cap), else_=Park.material + loot['material']),
        'baby_count': case((Park.baby_count + loot['babies'] > Park.baby_cap, Park.baby_cap), else_=Park.baby_count + loot['babies']),
        'child_count': case((Park.child_count + loot['children'] > max_child, max_child), else_=Park.child_count + loot['children']),
    })


def _format_battle_log(attacker, defender, attacker_wins, atk_losses, def_losses, loot,
                       send_guards=0, send_adults=0, boss_joins=False):
    """전투 결과를 텍스트 로그로 포맷"""
    lines = []
    lines.append(f"⚔️ {attacker.name} vs {defender.name}")
    lines.append(f"결과: {'🏆 공격자 승리!' if attacker_wins else '🛡️ 방어자 승리!'}")
    lines.append("")

    # 출정 편성 표시
    boss_text = " + 👑보스" if boss_joins else ""
    lines.append(f"[출정 편성] ⚔️경호 {send_guards} + 🧑성체 {send_adults}{boss_text}")
    lines.append("")

    lines.append(f"[공격자 피해]")
    lines.append(f"  ⚔️경호 -{atk_losses['guards']}, 🧑성체 -{atk_losses['adults']}")
    lines.append(f"[방어자 피해]")
    lines.append(f"  ⚔️경호 -{def_losses['guards']}, 🧑성체 -{def_losses['adults']}, "
                 f"👶자실장 -{def_losses.get('children', 0)}")

    if attacker_wins:
        lines.append("")
        lines.append(f"[약탈 내역]")
        lines.append(f"  🍬콘페이토: {loot['konpeito']}")
        lines.append(f"  🗑️음쓰: {loot['trash']}")
        lines.append(f"  🧱자재: {loot['material']}")
        lines.append(f"  🐛저실장: {loot['babies']}마리 포획")
        lines.append(f"  👶자실장: {loot['children']}마리 포획")

    return "\n".join(lines)
