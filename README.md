# 🏕️ 실장석 공원 제국 (Jissou Park Empire)

> *"콘페이토 맛있는 데스우~♪"*

---

## 🇰🇷 한국어

### 소개
**실장석 공원 제국**은 클래식 BBS 도어 게임(Ant War, Solar Realms Elite)에서 영감을 받은 턴제 전략 웹 게임입니다. 실장석(じっそうせき) 세계관을 기반으로 플레이어가 공원의 보스가 되어 실장석 군락을 경영합니다.

### 주요 기능
- 🏕️ **공원 경영**: 골판지집, 운치굴, 방벽 등 시설 건설
- 🌿 **채집 시스템**: 음식물 쓰레기(기본) + 콘페이토(희귀!) 수집
- 🐛 **3종 식량 체계**: 콘페이토(10NP), 저실장(5NP), 자실장(10NP), 음쓰(1NP)
- 🔪 **솞아내기**: 저실장/자실장을 식량 또는 자재로 전환
- ⚔️ **전투**: 경호실장 군대를 이끌고 타 공원 침공 & 약탈
- 🤖 **NPC 공원**: 5가지 성격(야만/요새/목장/교활/파괴자)의 AI 공원
- 📦 **교역 & 외교**: 공원 간 자원 교환, 동맹/적대 관계
- 🌐 **다국어 지원**: 한/영/일/중번/중간 5개 언어
- 🕵️ **밀사 시스템**: 적 공원 침투, 사보타주, 감시탑 방어
- 🌧️ **재해 이벤트**: 폭우/한파/살충제/쥐떼/고양이 등 랜덤 재해
- 🩸 **잔혹 시스템**: 카니발리즘, 질병, 반란, 중독, 출산 사고
- 👑 **보스 시스템**: 보스실장 사망 = 게임오버!
- 📱 **모바일 턴 쿼터**: 20분당 1턴 충전, 최대 15턴 보유 (반응형 UI)
- 🏆 **랭킹**: 전투력/인구/승률 기반 순위 시스템
- 🗣️ **실장석 대사**: 모든 행동에 "~데스", "~테커" 말투의 랜덤 대사
- 🎨 **Gore-Terminal 디자인 시스템**: 고밀도 인광 메인프레임 감성의 CRT 스캔라인 및 플리커링 오버레이 탑재, 3열 반응형 그리드 대시보드 개편
- 🧬 **가상 스킬 트리 (이스터에그)**: 향후 보스 스킬 시스템 확장을 대비해 SP 자동 충전 라이브 카운팅이 탑재된 가상 스킬 트리 모크업 터미널 연동

### 기술 스택
- **백엔드**: Python Flask + SQLAlchemy + SQLite
- **프론트엔드**: HTML/CSS/JS (레트로 터미널 스타일)
- **스케줄러**: APScheduler (턴 자동 처리)
- **배포**: 라즈베리파이 Linux + Nginx + Gunicorn

### 실행 방법
```bash
pip install -r requirements.txt
python run.py
```

---

## 🇺🇸 English

### Introduction
**Jissou Park Empire** is a turn-based strategy web game inspired by classic BBS door games (Ant War, Solar Realms Elite). Based on the Jissou (じっそうせき) universe, players become the boss of a park and manage a colony of Jissou creatures.

### Features
- 🏕️ **Park Management**: Build cardboard houses, dung caves, walls, and more
- 🌿 **Gathering System**: Collect food scraps (common) + Konpeito candy (rare!)
- 🐛 **3-Type Food System**: Konpeito(10NP), Baby(5NP), Child(10NP), Scraps(1NP)
- 🔪 **Culling (Mabiki)**: Convert baby/child Jissou into food or materials
- ⚔️ **Combat**: Lead guard Jissou armies to raid other parks
- 🤖 **NPC Parks**: AI parks with 5 personality types
- 📦 **Trade & Diplomacy**: Resource exchange, alliances, and rivalries
- 🌐 **Multilingual**: Korean, English, Japanese, Chinese (Traditional/Simplified)
- 🕵️ **Espionage**: Infiltrate enemy parks, sabotage, watchtower defense
- 🌧️ **Disasters**: Raids, cold waves, pesticides, rats, cats, dump removal
- 🩸 **Cruel Systems**: Cannibalism, disease, rebellion, addiction, birth tragedies
- 👑 **Boss System**: Boss Jissou death = Game Over!
- 📱 **Mobile Turn Quota**: 1 turn per 20min recharge, max 15 turns (Responsive UI)
- 🏆 **Rankings**: Power/population/win-rate based ranking
- 🗣️ **Jissou Dialogue**: Random "~desu", "~techu" voice lines
- 🎨 **Gore-Terminal Design System**: Highly-dense phosphorescent mainframe style with CRT scanline and flickering overlay, redesigned with a 3-column responsive grid dashboard.
- 🧬 **Virtual Skill Tree (Easter Egg)**: Virtual skill tree mockup terminal featuring live SP auto-charging counter, anticipating future Boss Skill expansion.

### Tech Stack
- **Backend**: Python Flask + SQLAlchemy + SQLite
- **Frontend**: HTML/CSS/JS (Retro terminal style)
- **Scheduler**: APScheduler (Turn auto-processing)
- **Deploy**: Raspberry Pi Linux + Nginx + Gunicorn

---

## 🇯🇵 日本語

### 紹介
**実装石公園帝国**は、クラシックなBBSドアゲーム（Ant War、Solar Realms Elite）からインスピレーションを得たターン制ストラテジーWebゲームです。実装石の世界観をベースに、プレイヤーは公園のボスとして実装石のコロニーを経営します。

### 主な機能
- 🏕️ **公園経営**: ダンボールハウス、ウンチ穴、防壁などの施設建設
- 🌿 **採集システム**: 食べ物ゴミ（一般）+ コンペイトウ（レア！）収集
- 🐛 **3種食糧体系**: コンペイトウ(10NP)、低実装(5NP)、子実装(10NP)、ゴミ(1NP)
- 🔪 **間引き**: 低実装/子実装を食糧または資材に変換
- ⚔️ **戦闘**: 護衛実装の軍隊を率いて他の公園を侵攻＆略奪
- 🤖 **NPC公園**: 5つの性格タイプのAI公園
- 📦 **交易&外交**: 公園間資源交換、同盟・敵対関係
- 🌐 **多言語対応**: 韓/英/日/中繁/中簡の5言語
- 🕵️ **密偵システム**: 敵公園潜入、サボタージュ、監視塔防御
- 🌧️ **災害イベント**: 豪雨/寒波/殺虫剤/ネズミ/猫 など
- 🩸 **残酷システム**: 共食、疫病、反乱、中毒、出産事故
- 📱 **モバイルターンクォータ**: 20分に1ターン充電、最大15ターン保有（レスポンシブUI）
- 🗣️ **実装石セリフ**: 全行動に「〜デス」「〜テチュ」のランダムボイス
- 🎨 **Gore-Terminalデザインシステム**: 高密度燐光メインフレーム感性のCRTスキャンラインおよびフリッカーオーバーレイ搭載、3列レスポンシブグリッドダッシュボードへの全面改修。
- 🧬 **仮想スキルツリー（イースターエッグ）**: 今後のボススキルシステム拡張を見据えた、SP自動充電ライブカウンター搭載の仮想スキルツリーモックアップ端末の連携。

---

## 🇹🇼 繁體中文

### 介紹
**實裝石公園帝國**是一款受經典BBS門遊戲（Ant War、Solar Realms Elite）啟發的回合制策略網頁遊戲。基於實裝石世界觀，玩家成為公園的老大，管理實裝石群落。

### 主要功能
- 🏕️ **公園經營**: 建造紙箱屋、糞穴、防壁等設施
- 🌿 **採集系統**: 收集食物垃圾（常見）+ 金平糖（稀有！）
- 🐛 **3種食糧體系**: 金平糖(10NP)、低實裝(5NP)、子實裝(10NP)、垃圾(1NP)
- 🔪 **間引**: 將低實裝/子實裝轉換為食糧或材料
- ⚔️ **戰鬥**: 率領護衛實裝軍隊入侵其他公園
- 🤖 **NPC公園**: 5種性格類型的AI公園
- 📦 **交易&外交**: 公園間資源交換、同盟與敵對關係
- 🌐 **多語言支援**: 韓/英/日/中繁/中簡 5種語言
- 🕵️ **密偵系統**: 滴入敵方公園、破壞、瞭望塔防禦
- 🌧️ **災害事件**: 暴雨/寒波/殺蟲劑/鼠群/貓等
- 🩸 **殘酷系統**: 同顟相食、疫病、叛亂、上癰、生產事故
- 📱 **行動輪配額**: 每20分鐘充電1輪，最多保有15輪（響應式UI）
- 🎨 **Gore-Terminal設計系統**: 搭載高密度磷光主機感性的CRT掃描線及閃爍覆蓋層，全面改版為3欄響應式網格儀表板。
- 🧬 **虛擬技能樹（彩蛋）**: 預留未來首領技能系統擴充，整合搭載SP自動充電即時計數器的虛擬技能樹樣板終端。

---

## 🇨🇳 简体中文

### 介绍
**实装石公园帝国**是一款受经典BBS门游戏（Ant War、Solar Realms Elite）启发的回合制策略网页游戏。基于实装石世界观，玩家成为公园的老大，管理实装石群落。

### 主要功能
- 🏕️ **公园经营**: 建造纸箱屋、粪穴、防壁等设施
- 🌿 **采集系统**: 收集食物垃圾（常见）+ 金平糖（稀有！）
- 🐛 **3种食粮体系**: 金平糖(10NP)、低实装(5NP)、子实装(10NP)、垃圾(1NP)
- 🔪 **间引**: 将低实装/子实装转换为食粮或材料
- ⚔️ **战斗**: 率领护卫实装军队入侵其他公园
- 🤖 **NPC公园**: 5种性格类型的AI公园
- 📦 **交易&外交**: 公园间资源交换、同盟与敌对关系
- 🌐 **多语言支持**: 韩/英/日/中繁/中简 5种语言
- 🕵️ **密探系统**: 渗透敌方公园、破坏、瞭望塔防御
- 🌧️ **灾害事件**: 暴雨/寒波/杀虫剂/鼠群/猫等
- 🩸 **残酷系统**: 同类相食、疫病、叛乱、上瘾、生产事故
- 📱 **行动轮配额**: 每20分钟充电1轮，最多保有15轮（响应式UI）
- 🎨 **Gore-Terminal设计系统**: 搭载高密度磷光主机感性的CRT扫描线及闪烁覆盖层，全面改版为3栏响应式网格仪表板。
- 🧬 **虚拟技能树（彩蛋）**: 预留未来首领技能系统扩充，整合搭载SP自动充电实时计数器的虚拟技能树样板终端。

---

## 라이선스 / License
MIT License

---

## 🗺️ Road Map

### 🇰🇷 차기 계획
- 🎨 **UI/UX 대규모 개편 (완료 - v1.7.0 Gore-Terminal 디자인 도입)**: CRT 효과 레이어 및 3열 반응형 그리드 탑재
- 📱 **안드로이드 솔플 APK**: Kivy/BeeWare 기반 네이티브 빌드 (Google Play 무료 배포)
- 🛡️ 보호 모드 밸런스 튜닝
- 🌐 멀티 버전: 기존 웹 버전 유지 (모바일 브라우저 접속)

### 🇺🇸 Upcoming
- 🎨 **UI/UX Major Overhaul (Completed - v1.7.0 Gore-Terminal Design)**: Implemented CRT effects and 3-column responsive grid dashboard
- 📱 **Android Solo APK**: Native build via Kivy/BeeWare (Free on Google Play)
- 🛡️ Protection mode balance tuning
- 🌐 Multiplayer: Keep existing web version (mobile browser access)

### 🇯🇵 今後の計画
- 🎨 **UI/UX大幅リニューアル（完了 - v1.7.0 Gore-Terminalデザイン導入）**: CRTエフェクトおよび3列レスポンシブグリッドを搭載
- 📱 **Android ソロAPK**: Kivy/BeeWare ネイティブビルド（Google Play無料配信）
- 🛡️ 保護モードバランス調整
- 🌐 マルチプレイ: 既存Web版維持（モバイルブラウザアクセス）

### 🇹🇼 未來計劃
- 🎨 **UI/UX大幅優化（已完成 - v1.7.0 Gore-Terminal設計導入）**: 搭載CRT特效與3欄響應式網格儀表板
- 📱 **Android 單人APK**: Kivy/BeeWare 原生構建（Google Play 免費發布）
- 🌐 多人版: 維持現有Web版（手機瀏覽器存取）

### 🇨🇳 未来计划
- 🎨 **UI/UX大幅优化（已完成 - v1.7.0 Gore-Terminal设计导入）**: 搭载CRT特效与3栏响应式网格仪表板
- 📱 **Android 单人APK**: Kivy/BeeWare 原生构建（Google Play 免费发布）
- 🌐 多人版: 维持现有Web版（手机浏览器访问）

