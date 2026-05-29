/**
 * 실장석 공원 제국 - 게임 스크립트 (game.js)
 * [v1.7.0] Gore-Terminal 전용 UI 인터랙션 및 AJAX 실시간 시뮬레이터 통합
 *
 * 모든 주석 및 경고 창 대사는 엄격히 '한국어'로만 기술됩니다.
 */

document.addEventListener('DOMContentLoaded', () => {
    // === 1. 플래시 메시지 자동 소멸 (8초 후 순차 소멸) ===
    const messages = document.querySelectorAll('.msg');
    messages.forEach((msg, i) => {
        setTimeout(() => {
            msg.style.opacity = '0';
            msg.style.transform = 'translateX(10px)';
            msg.style.transition = 'all 0.5s ease';
            setTimeout(() => msg.remove(), 500);
        }, 8000 + i * 1000);
    });

    // === 2. 솎아내기(Cull) 잔혹 확인 다이얼로그 (Crimson Alert) ===
    const cullButtons = document.querySelectorAll('.btn-cull');
    cullButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const form = btn.closest('form');
            const target = form.querySelector('[name="target_type"]').value;
            const count = form.querySelector('[name="count"]').value;
            const targetName = target === 'baby' ? '저실장' : '자실장';
            const emoji = target === 'baby' ? '🐛' : '👶';

            if (!confirm(`${emoji} ${targetName} ${count}마리를 정말 솎아내겠는 데스?\n\n"마마... 안 되는 데스/테츄... 프니프니해주는 데스..."`)) {
                e.preventDefault();
            }
        });
    });

    // === 3. 숫자 입력 유효성 방어 (최소/최대 클램핑) ===
    const numInputs = document.querySelectorAll('.num-input');
    numInputs.forEach(input => {
        input.addEventListener('change', () => {
            const min = parseInt(input.min) || 0;
            const max = parseInt(input.max) || 999;
            let val = parseInt(input.value) || 0;
            if (val < min) val = min;
            if (val > max) val = max;
            input.value = val;
        });
    });

    // === 4. 건설 드롭다운 설명 동적 업데이트 ===
    const buildSelect = document.getElementById('build-select');
    const buildDesc = document.getElementById('build-desc');
    const buildDescs = {
        'cardboard_house': '🏠 따뜻한 골판지집! 수용 인원 +15',
        'unchi_hole': '🕳️ 냄새가 지독하지만 유용! 저실장 수용 +10',
        'storage_hole': '📦 자원을 더 많이 보관! 콘페+25, 음쓰+100, 자재+50',
        'wall': '🧱 든든한 방벽! 방어력 20% 보너스',
        'watchtower': '🗼 적 전투력 정찰 가능!'
    };
    if (buildSelect && buildDesc) {
        const updateDesc = () => {
            const key = buildSelect.value;
            buildDesc.textContent = buildDescs[key] || '건물을 선택하세요';
        };
        buildSelect.addEventListener('change', updateDesc);
        updateDesc();
    }

    // === 5. 정찰(Scout) AJAX 통신 및 모달 렌더링 ===
    const scoutButtons = document.querySelectorAll('.btn-scout');
    scoutButtons.forEach(btn => {
        btn.addEventListener('click', async () => {
            const parkId = btn.getAttribute('data-park-id');
            const parkName = btn.getAttribute('data-park-name');
            const modal = document.getElementById('scout-modal');
            const overlay = document.getElementById('modal-overlay');
            const contentDiv = document.getElementById('scout-content');

            if (!modal || !contentDiv || !overlay) return;

            contentDiv.innerHTML = '<div class="animate-pulse">> CONNECTING SATELLITE...<br>> DECRYPTING DATA STREAM...</div>';
            modal.classList.remove('hidden');
            overlay.classList.remove('hidden');

            try {
                const response = await fetch(`/game/scout/${parkId}`);
                if (!response.ok) throw new Error('Satellite Offline');
                const data = await response.json();

                if (data.success) {
                    let html = `<div class="border-b border-outline-variant/30 pb-2 mb-2">
                        <strong>TERRITORY:</strong> ${parkName}<br>
                        <strong>STATUS:</strong> ACTIVE MAINframe
                    </div>`;

                    if (data.detailed) {
                        html += `
                        <div class="grid grid-cols-2 gap-2 text-[11px] mb-2">
                            <div>👥 ${I18N.scoutPopulation}: ${data.total_population}/${data.population_cap}</div>
                            <div>⚔️ ${I18N.scoutPower}: ${data.total_combat_power}</div>
                            <div>🛡️ ${I18N.scoutDefense}: ${data.defense_power}</div>
                            <div>🧱 ${I18N.scoutWalls}: ${data.walls}</div>
                            <div>❤️ ${I18N.scoutMorale}: ${data.morale}/100</div>
                        </div>
                        <div class="border-t border-dashed border-outline-variant/30 pt-2 text-[10px] text-text-dim">
                            💂 ${I18N.scoutGuards}: ${data.guard_count} |  성체: ${data.adult_count}<br>
                            자실장: ${data.child_count} | 저실장: ${data.baby_count}
                        </div>`;
                    } else {
                        html += `
                        <div class="space-y-1.5">
                            <div>👥 ${I18N.scoutPopulation}: ${data.total_population}</div>
                            <div class="text-error bg-error/10 border border-error/30 p-2 mt-2 font-label-kr">
                                🗼 ${I18N.scoutNeedTower}
                            </div>
                        </div>`;
                    }
                    contentDiv.innerHTML = html;
                } else {
                    contentDiv.innerHTML = `<div class="text-error">> ACCESS DENIED: ${data.error || I18N.scoutFail}</div>`;
                }
            } catch (err) {
                contentDiv.innerHTML = `<div class="text-error">> SYSTEM ERROR: ${err.message}</div>`;
            }
        });
    });

    // === 6. 침공(Attack) 모달 관리 및 실시간 전투력 예측 시뮬레이터 ===
    const attackOpenButtons = document.querySelectorAll('.btn-open-attack');
    attackOpenButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target-id');
            const targetName = btn.getAttribute('data-target-name');
            const modal = document.getElementById('attack-modal');
            const overlay = document.getElementById('modal-overlay');

            if (!modal || !overlay) return;

            document.getElementById('attack-target-id').value = targetId;
            document.getElementById('attack-title').innerHTML = `<span class="material-symbols-outlined text-sm">swords</span> INVASION: ${targetName}`;

            modal.classList.remove('hidden');
            overlay.classList.remove('hidden');

            // 초기 입력 리셋 및 예측 갱신
            document.getElementById('send-guards').value = 0;
            document.getElementById('send-adults').value = 0;
            document.getElementById('boss-joins').checked = false;
            updateAttackPreview();
        });
    });

    // === 7. 실시간 턴 카운트다운 타이머 연동 ===
    const turnTimer = document.getElementById('turnTimer');
    const turnCountdown = document.getElementById('turnCountdown');
    if (turnTimer && turnCountdown) {
        let seconds = parseInt(turnTimer.getAttribute('data-seconds')) || 0;
        if (seconds > 0) {
            const interval = setInterval(() => {
                seconds--;
                if (seconds <= 0) {
                    clearInterval(interval);
                    turnCountdown.textContent = '00:00';
                    location.reload(); // 즉시 새로고침하여 턴 충전 반영
                } else {
                    const mins = Math.floor(seconds / 60);
                    const secs = seconds % 60;
                    turnCountdown.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                }
            }, 1000);
        }
    }
});

// === [전역 함수] 침공 전투력 실시간 시뮬레이션 계산 (game.js 소속) ===
function updateAttackPreview() {
    const guardsInput = document.getElementById('send-guards');
    const adultsInput = document.getElementById('send-adults');
    const bossCheckbox = document.getElementById('boss-joins');
    const previewSpan = document.getElementById('atk-preview');

    if (!guardsInput || !adultsInput || !bossCheckbox || !previewSpan) return;

    const guards = parseInt(guardsInput.value) || 0;
    const adults = parseInt(adultsInput.value) || 0;
    const boss = bossCheckbox.checked;

    let power = guards * POWER_GUARD + adults * POWER_ADULT;
    
    if (boss) {
        power += POWER_BOSS;
    }

    // 보스 단독 출전 패널티 보정 (70% 수준으로 하락)
    if (boss && guards === 0 && adults === 0) {
        power = Math.floor(power * 0.7);
    }

    // 사기 효과에 따른 종합 보정계수 계산
    const moraleMult = 1.0 + (PARK_MORALE - 50) * MORALE_EFFECT / 50;
    const finalPower = Math.floor(power * moraleMult);

    previewSpan.textContent = finalPower.toLocaleString();
}
