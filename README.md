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
# 가상환경(venv) 생성 및 패키지 설치
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 가상환경 실행 후 기동
python3 run.py
# 또는 가상환경 외부에서 직접 기동:
venv/bin/python run.py
```

### 동시성 지원 매트릭스 (Concurrency Support Matrix)
본 프로젝트는 초경량 zero-setup 및 단일 서버 운영 환경을 기본으로 하여 SQLite를 채택하였으나, 다중 프로세스(Gunicorn) 다중 워커 프로덕션 환경의 동시성 안전성을 위해 설계되었습니다.

| 운영 조합 | 지원 여부 | 아키텍처 대응 및 완화 전략 |
|-----------|-----------|---------------------------|
| **SQLite + 단일 워커 (Single Worker)** | **공식 권장 (Supported)** | 개발 및 소형 호스팅에서 조건부 데이터 일관성(Consistency)을 유지하도록 설계되었습니다. SQLite WAL 활성화 및 내부 sequential lock으로 동시 쓰기 정합성을 소화합니다. 다만 SQLite 환경에서 `with_for_update()`는 실제 DB 행 락(Row Lock)을 걸지 않는 무효(no-op) 상태이므로, Flask 개발 서버 구동 시 thread 1개와 단일 동시 쓰기 조건 하에서만 정합성이 유지됩니다. |
| **SQLite + 다중 워커 (Multi Worker)** | **제한 지원 (Accepted Risk / Limited)** | 다중 프로세스 간의 DB 쓰기 경쟁 시 `Database Locked` 가능성이 존재합니다. busy_timeout=5000을 적용해 예외를 줄이지만, 경합 발생은 감수해야 할 한계(Accepted Risk)로 정의합니다. (※ 상세 사양: 책임자 Eunho Lim / DAU 100명 미만 또는 초당 DB 쓰기 10회 미만 한정 수용 / Database Locked 주 3회 감지 시 PostgreSQL 전환 조건부 수용) |
| **PostgreSQL/MySQL + 다중 워커** | **프로덕션 후보 (Target Production / Accepted Risk)** | 대규모 확장 및 다중 접속을 염두에 둔 조합입니다. 본 프로젝트의 2중 ID 정렬(Canonical Order) 락 획득 설계와 2단계 트랜잭션 경계 분리 구조가 PostgreSQL/MySQL 등 네이티브 행 락(Row Lock)과 상호 작용하도록 설계되어 있습니다. 교착 상태(Deadlock) 위험을 낮추는 방향이지만, 실제 검증은 별도 Accepted Risk 범주로 관리합니다. <br>※ **Accepted Risk 상세 규격 (PostgreSQL/MySQL 실 DB row-lock/deadlock 미검증)**:<br>- **책임자(Owner)**: `Project Lead Architect / Eunho Lim`<br>- **수용 사유**: 현재 개발/테스트 인프라 제약으로 인해 실제 PostgreSQL/MySQL 인스턴스를 통한 다중 worker 부하 및 row-lock/deadlock E2E 검증은 수행하지 않았으며, ID Canonical Ordering 설계적 안전성만 확인한 상태에서 운영 위험을 제한적으로 수용함.<br>- **만료 조건**: 프로덕션 DB로 실제 PostgreSQL/MySQL 이주 완료 및 해당 DB 상에서 다중 스레드 부하 테스트/교착 검증 스위트를 최초로 수행 및 통과하는 시점.<br>- **재검토 조건**: 실제 RDBMS 프로덕션 이주 후 lock timeout 또는 deadlock 경보가 시스템 상에서 최초로 주 1회 이상 감지되는 시점. |

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

### Concurrency Support Matrix
This project adopts SQLite by default for lightweight, zero-setup operation, but is designed for concurrency safety in multi-process (Gunicorn) multi-worker production environments.

| Deployment Combo | Support Level | Architectural Strategy & Mitigation |
|-------------------|---------------|--------------------------------------|
| **SQLite + Single Worker** | **Recommended (Supported)** | Stable consistency for development and small-scale hosting. Concurrent writes are handled safely via SQLite WAL and internal sequential locks under single-thread and single-writer constraints. Note that `with_for_update()` acts as a no-op in SQLite, which does not enforce real row-level locking. |
| **SQLite + Multi Worker** | **Limited (Accepted Risk)** | Potential `Database Locked` errors may occur under concurrent write competition. Enforced `PRAGMA busy_timeout=5000` minimizes exceptions, but race conditions under heavy load are defined as an accepted risk. (Owner: Eunho Lim / Expiry: >100 DAU or >10 writes/sec / Review Trigger: Locked error >=3 times a week, requiring immediate PostgreSQL migration). |
| **PostgreSQL/MySQL + Multi Worker** | **Target Production (Accepted Risk)** | Optimal combo for large-scale scaling and high-concurrency hosting. The 2-way ID-sorted (Canonical Order) locking and two-stage transaction separation integrate natively with row locks to reduce deadlock risk and support concurrency. <br>※ **Accepted Risk Specifications (PostgreSQL/MySQL Real Instance Unverified)**:<br>- **Owner**: `Project Lead Architect / Eunho Lim`<br>- **Reason**: Due to dev/test infrastructure constraints, E2E multi-worker load and row-lock/deadlock validation on real PostgreSQL/MySQL instances were not performed. Concurrency is designed on ID Canonical Ordering, but unverified real DB locking is accepted as a potential operational risk.<br>- **Expiry Condition**: Completion of production migration to real PostgreSQL/MySQL and successful completion of the first multi-threaded load/deadlock validation suite.<br>- **Recheck Condition**: First detection of any lock timeout or deadlock alarm >=1 time a week in production. |

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

### 同時実行サポートマトリックス (Concurrency Support Matrix)
本プロジェクトは軽量でゼロ設定の運用のためにSQLiteをデフォルトで採用していますが、マルチプロセス（Gunicorn）マルチワーカーの本番環境における同時実行安全性を考慮して設計されています。

| 運用環境 | サポート状況 | 設計的対応および緩和戦略 |
|----------|--------------|-------------------------|
| **SQLite + シングルワーカー (Single Worker)** | **公式推奨 (Supported)** | 開発および小規模ホスティングで条件付きの一貫性（Consistency）が維持されます。SQLite WALの有効化と内部的な順序ロックにより安全に処理されます。ただし、SQLite環境において `with_for_update()` は実際の行ロック（Row Lock）をかけない無効（no-op）状態であるため、Flask開発サーバーのthread 1つおよび単一同時書き込みの制限下でのみ整合性が維持されます。 |
| **SQLite + マルチワーカー (Multi Worker)** | **制限付きサポート (Accepted Risk / Limited)** | 複数プロセス間の同時書き込み競合時に `Database Locked` が発生する可能性があります。busy_timeout=5000 を注入して例外を最小限に抑えますが、高負荷時の競合は許容されるリスク（Accepted Risk）と定義します。（※詳細仕様：責任者 Eunho Lim / DAU 100人未満または秒間書き込み10回未満の制限的な許容 / Database Lockedが週3回以上検出された場合、PostgreSQLへ即時移行） |
| **PostgreSQL/MySQL + マルチワーカー** | **本番候補 (Target Production / Accepted Risk)** | 大規模スケーリングと高同時実行向けの組合せです。本プロジェクトの2重ID整列（Canonical Order）悲観的ロック設計と2段階トランザクション境界分離構造が、PostgreSQL/MySQLなどのネイティブ行ロック（Row Lock）と連携しながら同時実行を支援する想定です。 <br>※ **Accepted Risk 詳細仕様 (PostgreSQL/MySQL 実DB row-lock/deadlock 未検証)**:<br>- **責任者(Owner)**: `Project Lead Architect / Eunho Lim`<br>- **受容理由**: 現在の開発/テストインフラの制約により、実際のPostgreSQL/MySQLインスタンスを使用したマルチワーカー負荷およびrow-lock/deadlockのE2E検証は行っておらず、ID Canonical Orderingによる設計的安全性のみを確認した状態で運用のリスクを限定的に受容します。<br>- **満了条件**: 本番DBとして実際のPostgreSQL/MySQLへの移行が完了し、当該DB上でのマルチスレッド負荷テスト/デッドロック検証スイートを初めて実施および通過した時点。<br>- **再検討条件**: 実際のRDBMS本番移行後、システム上でlock timeoutまたはdeadlockのアラームが初めて週1回以上検出された時点。 |

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

### 併發支援矩陣 (Concurrency Support Matrix)
本專案默認採用 SQLite 以實現輕量化、零設定運作，但專為多進程（Gunicorn）多工作線程（Multi Worker）生產環境的併發安全性而設計。

| 部署組合 | 支援層級 | 架構策略與緩解機制 |
|----------|----------|-------------------|
| **SQLite + 單工作線程 (Single Worker)** | **官方推薦 (Supported)** | 在單線程與單寫入限制條件下，維持開發和小規模託管的一致性（Consistency）。併發寫入透過 SQLite WAL 和內部順序鎖安全處理。請注意，`with_for_update()` 在 SQLite 下為無效操作（no-op），不提供真實的原生行級鎖，因此僅在 Flask 開發伺服器單一執行緒與單一寫入限制下維持一致性。 |
| **SQLite + 多工作線程 (Multi Worker)** | **限制支援 (Accepted Risk / Limited)** | 在併發寫入競爭下可能會出現 `Database Locked` 錯誤。透過強制注入 `PRAGMA busy_timeout=5000` 來最小化異常，但高負載下的競爭被定義為可接受的風險（Accepted Risk）。（※詳細規格：負責人 Eunho Lim / DAU < 100 或每秒寫入 < 10 次限制接受 / 週偵測鎖錯誤 >= 3 次時即刻強制轉移至 PostgreSQL）。 |
| **PostgreSQL/MySQL + 多工作線程** | **官方生產目標 (Target Production / Accepted Risk)** | 大規模擴展和高併發託管的主要組合。雙向 ID 排序（Canonical Order）悲觀鎖與兩階段事務邊界分離結構可與 PostgreSQL/MySQL 等原生行鎖（Row Lock）配合，降低死鎖風險並支援併發。 <br>※ **Accepted Risk 詳細規格 (PostgreSQL/MySQL 實DB row-lock/deadlock 未驗證)**:<br>- **負責人(Owner)**: `Project Lead Architect / Eunho Lim`<br>- **接受理由**: 由於目前開發/測試基礎設施的限制，尚未通過實際的 PostgreSQL/MySQL 實例進行多工作線程負載及 row-lock/deadlock 的 E2E 驗證，在僅確保 ID Canonical Ordering 設計安全性的情況下，暫時接受潛在的運作風險。<br>- **滿期條件**: 完成將生產環境實際轉移至 PostgreSQL/MySQL，並首次在該資料庫上執行並通過多線程負載測試/死鎖驗證套件。<br>- **重新評估條件**: 實際轉移至 RDBMS 生產環境後，系統首次偵測到 lock timeout 或 deadlock 警報達到每週 1 次以上。 |

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

### 并发支持矩阵 (Concurrency Support Matrix)
本项目默认采用 SQLite 以实现轻量化、零配置运行，但专为多进程（Gunicorn）多工作线程（Multi Worker）生产环境的并发安全性而设计。

| 部署组合 | 支持层级 | 架构策略与缓解机制 |
|----------|----------|-------------------|
| **SQLite + 单工作线程 (Single Worker)** | **官方推荐 (Supported)** | 在单线程与单写入限制条件下，维持开发和小规模托管的一致性（Consistency）。并发写入通过 SQLite WAL 和内部顺序锁安全处理。请注意，`with_for_update()` 在 SQLite 下为无效操作（no-op），不提供真实的原生行级锁。 |
| **SQLite + 多工作线程 (Multi Worker)** | **限制支持 (Accepted Risk / Limited)** | 在并发写入竞争下可能会出现 `Database Locked` 错误。通过强制注入 busy_timeout=5000 来最小化异常，但高负载下的竞争被定义为可接受的风险（Accepted Risk）。（※详细规格：负责人 Eunho Lim / DAU < 100 或每秒写入 < 10 次限制接受 / 周侦测锁错误 >= 3 次时即刻强制转移至 PostgreSQL）。 |
| **PostgreSQL/MySQL + 多工作线程** | **官方生产目标 (Target Production / Accepted Risk)** | 大规模扩展和高并发托管的主要组合。双向 ID 排序（Canonical Order）悲观锁与两阶段事务边界分离结构能与 PostgreSQL/MySQL 等原生行锁（Row Lock）配合，降低死锁风险并支持并发。 <br>※ **Accepted Risk 详细规格 (PostgreSQL/MySQL 实DB row-lock/deadlock 未验证)**:<br>- **负责人(Owner)**: `Project Lead Architect / Eunho Lim`<br>- **接受理由**: 由于目前开发/测试基础设施的限制，尚未通过实际的 PostgreSQL/MySQL 实例进行多工作线程负载及 row-lock/deadlock 的 E2E 验证，在仅确保 ID Canonical Ordering 设计安全性的情况下，暂时接受潜在的运作风险。<br>- **满期条件**: 完成将生产环境实际转移至 PostgreSQL/MySQL, 并首次在该数据库上运行并通过多线程负载测试/死锁验证套件。<br>- **重新评估条件**: 实际转移至 RDBMS 生产环境后，系统首次侦测到 lock timeout 或 deadlock 警报达到每周 1 次以上。 |

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
- 🌐 **多人版**: 维持现有Web版（手机浏览器访问）

---

## 🛠️ Troubleshooting / 문제 해결

### 🇰🇷 한국어
- **Q: 대시보드와 게임 행동 중 동시성 Lost Update가 발생하나요?**
  - **A:** [v1.8.0] 보호 모드 자원 보충(`check_and_enter_protection`) 시 비관적 락(`with_for_update()`)과 데이터 동기화(`refresh`)가 적용되어 동시 요청 환경에서 데이터 훼손 가능성을 줄입니다.
- **Q: 게임오버 후 재시작 시 로그인 화면으로 튕기며 무한 리다이렉트가 일어나나요?**
  - **A:** [v1.8.0] 재시작 트랜잭션이 원자적으로 통합되었으며, 공원이 유실된 유저에게는 루트 및 로그인 진입 시 기본 공원이 자동 복구되도록 구성되어 무한 루프 가능성을 줄입니다.
- **Q: 다중 프로세스(Gunicorn 멀티 워커) 환경에서 교역 한도 우회나 NPC 중복 턴(NPC Stampede)이 발생하나요?**
  - **A:** [v1.8.1] 기존 파이썬 스레드 락(`threading.Lock`)을 DB 비관적 락(`with_for_update()`) 및 `turn_count` 선행 동기화 가드로 전면 대체하여 프로세스 장벽을 넘는 동시성 직렬화를 유지하도록 구성했습니다.
- **Q: 플레이어 공격 시 NPC 자원 덮어쓰기(Lost Update) 및 NPC 턴 예외 시 자원 증식 버그가 있나요?**
  - **A:** [v1.8.1] NPC 자연 성장을 단일 원자적 `UPDATE`로 전환하여 `autoflush` Lost Update를 방어하였고, 범용 엔진 기능에 `commit=False` 제어권을 인입해 NPC 턴 전체가 원자적 단일 트랜잭션 내에서 처리 및 롤백되도록 안전 조치하였습니다.
- **Q: 행동 실행 도중 자원 부족이나 유효성 검사 실패 등으로 실패했을 때, 선행 차감된 AP(행동포인트)가 증발하나요?**
  - **A:** [v1.8.2] 행동이 실패(`not success`)할 경우, 이미 `consume_turn`에 의해 선행 커밋된 AP를 플레이어에게 돌려주는 공용 보상 트랜잭션(`game_engine.refund_ap`)이 동작하므로 AP가 불필요하게 유실되는 자원 누수(AP Leakage) 현상을 줄입니다.
- **Q: 턴이 지나면서 공원이 멸망한 상태에서 행동을 한 번 더 하거나, 멸망한 공원과 교역/전투가 일어날 수 있나요?**
  - **A:** [v1.8.3] `consume_turn`에서 턴 소비로 인해 공원이 멸망하면 즉시 조기 기각되고 차단되며, 교역 수락(`trade_accept`) 및 전투(`execute_battle`)에서도 비관적 락을 획득한 직후 상대방의 멸망 상태를 재검증하므로 좀비 행동(Zombie Action) 및 TOCTOU 결함 위험을 줄입니다.
- **Q: 상대방 공원이 삭제(재시작)될 때, 내가 제안했던 교역 자원이나 파견된 밀사(성체실장)가 사라지나요?**
    - **A:** [v1.8.4] 데이터베이스 삭제 전(`before_delete`) 이벤트 리스너를 도입하여, 상대방이 `/restart` 등으로 공원을 삭제해 교역이나 밀사가 Cascade Delete될 때, 대기 중이던 에스크로 자원 및 파견 중인 성체실장을 자동으로 발신자 공원에 되돌려줍니다(cap 한도 적용). 자원 유실(Resource Leakage) 위험을 줄입니다.
- **Q: 두 공원이 동시에 서로에게 외교 요청(동맹/적대)을 보낼 때, 중복 관계가 생성되거나 모순된 상태(동맹이자 적대)가 발생하나요?**
  - **A:** [v1.8.5] 두 공원 간의 외교 관계 저장 시 항상 `park_a_id < park_b_id`를 만족하는 Canonical Ordering 및 `initiator_id` 컬럼을 적용하여 Unique 제약이 중복 생성을 억제합니다. 또한, 외교 처리 시 ID 오름차순의 2중 비관적 락을 일괄 획득하여 교착 상태 위험을 낮추고, 관계 변경 시 벌크 쿼리(`update()`)를 통한 일괄 상태 해제를 가동하여 "동맹이자 적대"라는 모순 상태와 상태 해제 누락 현상을 정리합니다.
- **Q: NPC 일괄 턴 동기화 시 중간 커밋으로 인해 다른 플레이어가 개입하여 락이 유실되거나 Lost Update가 발생하나요?**
  - **A:** [v1.8.6] 루프 외부에서 모든 NPC를 한 번에 락킹한 뒤 루프 내부에서 커밋하던 구조적 한계를 개선했습니다. 루프 외부에서는 오직 ID 목록만 추출하고, 루프 내부에서 **개별 트랜잭션 단위로 각 NPC를 조회하고 비관적 락(`with_for_update()`)**을 확보해 격리 처리합니다. 또한, NPC 행동 중 예외가 발생하더라도 **Nested Transaction (Savepoint, `begin_nested()`)**을 기동하여 전체 비관적 락 유실 및 턴 정보 롤백 가능성을 낮추도록 조치했습니다. 밀사 사보타주 시에도 2-Way Lock을 걸어 계산 격차(TOCTOU)를 완화했습니다.
- **Q: 교역 거절 시 악의적인 유저가 임의의 교역 ID를 변조하여 타인의 프라이빗 교역을 강제로 거절(IDOR)할 수 있나요? 또한 멸망한 유저의 교역(Zombie Trades)이 시장에 지속 노출되나요?**
  - **A:** [v1.8.7] 교역 거절(`trade_reject`) API의 원자적 UPDATE 조건식에 `receiver_id == park.id` 가드 조건을 추가하여 오직 제안을 받은 본인만 거절할 수 있도록 인가(Authorization)를 적용해 IDOR 취약점을 낮췄습니다. 또한, 멸망한 유저의 교역 제안이 시장에 지속 노출되는 좀비 거래 현상을 줄이기 위해 `trade_market()` 쿼리 단계에서 `Park` 모델을 JOIN하여 발송자가 살아있는(`is_destroyed == False`) 교역 제안만 동적으로 걸러서 보여주도록 정리했습니다.
- **Q: 슬로우 패스(턴 소비 및 NPC 동기 턴 진행) 실행 도중, 다른 비동기 요청이 AP를 차감할 때 메모리 덮어쓰기(Lost Update)로 AP가 복제(무상 사용)되나요?**
  - **A:** [v1.8.8] `consume_turn()` 슬로우 패스에서 `process_turn()` 및 `_sync_npc_turns()`를 기동하는 도중 플레이어 락이 해제되어 비동기 다중 요청(패스트 패스)이 AP를 차감하여 성공하더라도, 슬로우 패스 끝단에서 **다시 플레이어 공원 락을 획득하고 최신 상태로 새로고침(`refresh`)** 한 뒤 최종 AP 감산을 진행하도록 보강하여 AP 복제(Lost Update) 결함을 완화했습니다. (audit_report_56.md [STATE-F029])
- **Q: NPC 턴 진행 중 전투 발생 시 `ResourceClosedError` 등으로 턴 동기화 루프가 깨지거나 무한 루프가 발생하나요? 또한 행동 실패 시 환불된 AP가 유실되는 현상이 있나요? 밀사 귀환 후 overcrowding 처리 시 Lost Update로 자원이 사라지거나 중복될 수 있나요?**
  - **A:** [v1.8.9] 세부 사항을 조정했습니다. NPC의 전투 기동 내부 `commit()`을 `flush()`로 변경해 중첩 세이브포인트를 지키고 2중 롤백 예외 방어로 안정을 높였습니다. 환불 `refund_ap` 작동 후 라우터 단에서 즉각 명시적 `db.session.commit()`을 수행해 롤백 유실을 막았으며, 밀사 임무 처리(`_process_spy_missions`) 끝단에서 과밀도 처리 전 다시 한번 플레이어 공원의 `with_for_update()` 비관적 락을 걸고 `refresh`를 실행하여 concurrent 다중 요청에 의한 데이터 덮어쓰기(Lost Update)를 낮췄습니다.
- **Q: NPC가 플레이어 또는 다른 공원을 공격할 때 락 획득 순서가 꼬여 교착 상태(Deadlock)가 발생하고 DB 커넥션이 고갈되나요?**
  - **A:** [v1.8.9] 설계적으로 교착 상태 취약점`[DEADLOCK-F005]`을 낮췄습니다. 기존 `process_npc_turn()` 시작 부분에서 무조건적으로 대상 NPC 공원 레코드를 선점 락킹하던 비관적 락(`with_for_update()`)을 제거하고 단순 리프레시만 전개하는 동시에, 상위 턴 동기화 스케줄러 `_sync_npc_turns()`에서 NPC 기본 턴 처리(`process_turn`) 완료 즉시 `db.session.commit()`을 실행하여 선점 락을 해제한 후 `process_npc_turn()`을 독립된 트랜잭션으로 기동하는 **2단계 트랜잭션 경계 분리 구조**를 적용했습니다. 이로 인해 NPC가 공격 행동을 취할 때 오직 `execute_battle()` 내부에서만 두 공원의 락을 Canonical Ordering(ID 오름차순 정렬) 순으로 획득하도록 구성해 상호 락 대기 충돌에 의한 데드락 및 DB 커넥션 풀 고갈 결함 발생 위험을 낮췄습니다 (단, 실제 PostgreSQL/MySQL 인스턴스 환경의 E2E 및 부하 검증은 Accepted Risk 상태로 유지됩니다).

### 🇺🇸 English
- **Q: Does concurrent Lost Update occur during dashboard and game actions?**
  - **A:** [v1.8.0] A pessimistic lock (`with_for_update()`) and data synchronization (`refresh`) are applied during protection mode bailout, helping reduce the chance of data loss under concurrent actions.
- **Q: Does an infinite redirect occur after clicking restart and getting bounced to login?**
  - **A:** [v1.8.0] Restart is now atomic, and any authenticated user with a missing park will automatically have a default park reconstructed instantly, preventing redirect loops.
- **Q: Does trade limit bypass or duplicated NPC turns (NPC Stampede) occur in a multi-process (Gunicorn) environment?**
  - **A:** [v1.8.1] Thread locks (`threading.Lock`) have been replaced with database-level pessimistic locks (`with_for_update()`) combined with sequential ID locking and a `turn_count` synchronization guard, helping prevent process-safe serialization issues and minimizing concurrency conflicts.
- **Q: Is there any issue with overwritten NPC resources (Lost Update) on player attacks or infinite resource bugs on NPC turn exceptions?**
  - **A:** [v1.8.1] NPC passive growth is now an atomic SQL `UPDATE` to reduce `autoflush` Lost Updates, and intermediate commits are suppressed (`commit=False`) during NPC actions, so the NPC turn executes and rolls back inside a single atomic transaction.
- **Q: Do prior action points (AP) evaporate when an action fails due to insufficient resources or validation failure during execution?**
  - **A:** [v1.8.2] In case of action failure (`not success`), a compensating transaction (`game_engine.refund_ap`) is triggered to safely return the pre-deducted AP to the player, eliminating any potential AP leakage or ghost deduction.
- **Q: Is it possible for a player to take a zombie action after their park is destroyed, or trade/fight with an already destroyed park?**
  - **A:** [v1.8.3] If a park gets destroyed due to turn progression inside `consume_turn`, the action is instantly aborted. Furthermore, `trade_accept` and `execute_battle` double-check the destruction state right after acquiring pessimistic locks, reducing zombie-action and TOCTOU risk.
- **Q: When the opponent's park is deleted (restarted), do my proposed trade resources or dispatched spy units (adults) evaporate permanently?**
  - **A:** [v1.8.4] By introducing database-level `before_delete` event listeners, if a trade offer or spy mission is cascade-deleted due to the opponent executing a `/restart`, any pending escrow resources and active spy units are automatically refunded to the sender (applying cap clamping). This reduces the chance of resource leakage.
- **Q: When two parks send diplomatic requests (alliance/hostility) to each other simultaneously, do duplicate relationships or contradictory states (both allied and hostile) occur?**
  - **A:** [v1.8.5] By enforcing Canonical Ordering (`park_a_id < park_b_id`) and utilizing the `initiator_id` column when saving diplomatic relations, the database UniqueConstraint helps block duplicate records. Additionally, we enforce ID-sorted 2-Way pessimistic locking to reduce deadlocks, and use bulk updates (`update()`) to dissolve all active/pending duplicate relations between the two parks simultaneously, helping avoid contradictory states.
- **Q: During concurrent NPC turn synchronizations, do intermediate commits cause lock loss or Lost Updates?**
  - **A:** [v1.8.6] Yes, we resolved the structural limitation where locking all NPCs at once resulted in early lock releases inside the loop due to intermediate commits. We now query only NPC IDs outside the loop, and inside the loop, we query and acquire a pessimistic lock (`with_for_update()`) on each NPC park in **individual isolated transactions**. Additionally, if an action fails, a **Nested Transaction (Savepoint, `begin_nested()`)** is utilized to roll back only the failed action, protecting the overall pessimistic lock and preventing turn count rollbacks (Stampede). Spy sabotage is also guarded with a 2-Way Lock to eliminate the TOCTOU calculation window.
- **Q: When rejecting a trade, can a malicious user tamper with the trade ID to force-reject someone else's private trade (IDOR)? Also, do trade offers from destroyed users (Zombie Trades) persist in the market?**
  - **A:** [v1.8.7] We mitigated the IDOR vulnerability by adding the `receiver_id == park.id` guard condition to the atomic UPDATE query of the `trade_reject` API, so that only the designated recipient can reject private trade offers. Furthermore, to reduce "Zombie Trades" from persisting in the market, we modified the `trade_market()` query to JOIN the `Park` model and dynamically filter out pending trade offers from senders who have already been destroyed (`is_destroyed == False`).
- **Q: During the slow-path (turn progression & NPC synchronization), if concurrent asynchronous requests deduct AP, does AP duplication (Lost Update) occur due to stale memory overwrites?**
  - **A:** [v1.8.8] We substantially reduced the AP duplication (Lost Update) flaw. Even if concurrent fast-path requests successfully deduct AP during the lock-free synchronization gap of the slow-path, the end of the slow-path **re-acquires the player's pessimistic lock and enforces a database `refresh`** before performing the final AP subtraction, helping keep computations atomic and up to date. (audit_report_56.md [STATE-F029])
- **Q: During NPC turns, does battle cause `ResourceClosedError` disrupting turn sync or infinite loop? Also, is there any loss of refunded AP on action failures, or Lost Update causing resource duplication/loss when resolving overcrowding after spy return?**
  - **A:** [v1.8.9] Mitigated for the current supported path. NPC battle commit has been changed to `flush()` to preserve nested savepoints, protected by a double-rollback exception guard. Refunded AP is persisted by executing explicit `db.session.commit()` directly at the router exception block. Finally, before resolving overcrowding in `_process_spy_missions`, we acquire a `with_for_update()` pessimistic lock and perform `refresh` on the player park, helping prevent concurrent requests from overwriting data (Lost Update).
- **Q: Does a lock order inversion occur when an NPC attacks a player or another park, causing a deadlock and database connection exhaustion?**
  - **A:** [v1.8.9] The deadlock vulnerability `[DEADLOCK-F005]` has been reduced with a two-stage design. We have removed the pessimistic lock (`with_for_update()`) that was pre-acquired at the start of `process_npc_turn()`, replacing it with a simple `refresh`. Concurrently, we introduced a **two-stage transaction boundary separation** in the synchronization scheduler `_sync_npc_turns()`, which forces `db.session.commit()` immediately after finishing the basic NPC turn processing (`process_turn`) to release any pre-acquired locks before spawning the independent `process_npc_turn()` AI action. As a result, when an NPC initiates an attack, locks for both parks are acquired concurrently only inside `execute_battle()` according to Canonical Ordering (sorted by ID in ascending order). This helps prevent lock order inversion deadlock conflicts and DB connection pool exhaustion (Note: E2E concurrency validation on real PostgreSQL/MySQL instances remains an Accepted Risk).

### 🇯🇵 日本語
- **Q: ダッシュボードとゲームの操作が同時に行われると、Lost Update は起こりますか？**
  - **A:** [v1.8.0] 保護モードでは `with_for_update()` の悲観的ロックと `refresh` により、並行要求でもデータの上書きが起きにくい設計です。
- **Q: 再起動後にログイン画面へ戻され、無限リダイレクトになりますか？**
  - **A:** [v1.8.0] 再起動処理は単一トランザクションにまとめており、公園を失った利用者には既定の公園を自動再生成するため、循環を抑えます。
- **Q: 多重プロセス環境で交易制限の回避や NPC の重複ターンは起こりますか？**
  - **A:** [v1.8.1] スレッドロックを使わず、DB レベルの悲観的ロックと `turn_count` 同期ガードで、プロセスをまたぐ直列化を維持します。
- **Q: プレイヤーの攻撃時に NPC の資源が上書きされたり、例外時に資源が増殖したりしますか？**
  - **A:** [v1.8.1] NPC の自然成長を単一の原子的 `UPDATE` に変え、`autoflush` による上書きを抑えています。NPC ターン全体も単一トランザクション内で実行とロールバックが行われます。
- **Q: 行動実行中に資源不足や検証失敗が起きた場合、AP は失われますか？**
  - **A:** [v1.8.2] 失敗時は補償トランザクション（`game_engine.refund_ap`）で、先に差し引いた AP を返還します。
- **Q: ターン進行で公園が滅亡した後も行動や交易、戦闘はできますか？**
  - **A:** [v1.8.3] `consume_turn` により公園が滅亡した場合は即時中断します。交易や戦闘でも、悲観的ロック取得直後に滅亡状態を再確認するため、ゾンビ行動や TOCTOU の脆弱性を抑えます。
- **Q: 相手の公園が削除されたとき、提案した交易資源や派遣した密使は失われますか？**
  - **A:** [v1.8.4] `before_delete` イベントリスナーにより、`/restart` などで相手が公園を削除しても、待機中のエスクロー資源と派遣中の密使は送信者へ返還されます。
- **Q: 二つの公園が同時に外交要請を送ると、重複関係や矛盾状態は発生しますか？**
  - **A:** [v1.8.5] `park_a_id < park_b_id` の Canonical Ordering と `initiator_id` により重複を抑えます。ID 昇順の 2 重悲観的ロックとバルク更新で、矛盾状態や解除漏れも抑えます。
- **Q: NPC の一括ターン同期で中間コミットが入ると、ロックが失われますか？**
  - **A:** [v1.8.6] ループ外では ID 一覧のみを取り、ループ内で各 NPC を個別トランザクションとして悲観的ロックします。例外時は `begin_nested()` で失敗分のみを戻し、全体のロックとターン情報を保ちます。
- **Q: 交易拒否時に、他人の取引を勝手に拒否できたり、滅亡済みユーザーの取引が市場に残ったりしますか？**
  - **A:** [v1.8.7] `trade_reject` の UPDATE 条件に `receiver_id == park.id` を加え、受信者本人だけが拒否できるようにしました。`trade_market()` では `Park.is_destroyed == False` を絞り込み、滅亡済みの提案は表示しません。
- **Q: スローパス実行中に他の非同期要求が AP を差し引くと、AP が複製されますか？**
  - **A:** [v1.8.8] スローパス終端で再度悲観的ロックを取得し、`refresh` で最新状態を読んでから最終減算するため、Lost Update を抑えます。 (audit_report_56.md [STATE-F029])
- **Q: NPC の戦闘中に `ResourceClosedError` などで同期ループが壊れたり、AP や資源が失われたりしますか？**
  - **A:** [v1.8.9] NPC 戦闘内部の `commit()` を `flush()` に置き換え、入れ子のセーブポイントを保護しました。返還 AP は例外ブロックで即時コミットし、過密処理前には `with_for_update()` と `refresh` を行うため、並行要求による書き換えを抑えます。
- **Q: NPC が攻撃するとき、ロック順序の逆転でデッドロックや接続枯渇は起こりますか？**
  - **A:** [v1.8.9] `process_npc_turn()` の先行ロックを外し、`_sync_npc_turns()` 側で基本ターン完了後に `commit()` して先行ロックを解放する構成にしました。攻撃時のロック取得は `execute_battle()` 内の Canonical Ordering に集約されるため、デッドロックの起きにくい流れです。
### 🇹🇼 繁體中文
- **Q: 儀表板與遊戲操作同時進行時，會發生 Lost Update 嗎？**
  - **A:** [v1.8.0] 保護模式下已套用悲觀鎖（`with_for_update()`）與資料同步（`refresh`），可降低併發請求覆寫資料的風險。
- **Q: 重新開始後會跳回登入畫面並出現無限重新導向嗎？**
  - **A:** [v1.8.0] 重新開始流程已整合為單一原子處理，若偵測到使用者失去公園，系統會自動重建預設公園，降低循環風險。
- **Q: 多程序環境下會出現交易限制繞過或 NPC 重複執行回合嗎？**
  - **A:** [v1.8.1] 已改用資料庫層級的悲觀鎖（`with_for_update()`）搭配 `turn_count` 同步防護，維持跨程序的直列化。
- **Q: 使用者攻擊 NPC 時，會發生資源被覆寫或例外時產生不當複製嗎？**
  - **A:** [v1.8.1] 已將 NPC 自然成長改為單一原子化 SQL `UPDATE`，以避免 `autoflush` 覆寫，並使整個 NPC 回合在單一交易內執行與回滾。
- **Q: 行動執行中若因資源不足或驗證失敗而中斷，先前扣除的 AP 會消失嗎？**
  - **A:** [v1.8.2] 當行動失敗時，系統會啟動補償交易（`game_engine.refund_ap`），將已先行扣除的 AP 返還給玩家。
- **Q: 隨著回合推進公園已滅亡時，還能再執行行動或與其交易、戰鬥嗎？**
  - **A:** [v1.8.3] 若 `consume_turn` 導致公園滅亡，行動會立即中止。交易與戰鬥在取得悲觀鎖後也會再驗證滅亡狀態，以降低殭屍行動與 TOCTOU 風險。
- **Q: 對方公園被刪除時，我提議的交易資源或派遣的密使會持續消失嗎？**
  - **A:** [v1.8.4] 透過 `before_delete` 事件監聽器，對方執行 `/restart` 導致交易或密使被級聯刪除時，系統會把待處理的託管資源與執行中的密使返還給發送方公園。
- **Q: 兩個公園同時互送外交請求時，會產生重複關係或矛盾狀態嗎？**
  - **A:** [v1.8.5] 以 `park_a_id < park_b_id` 的 Canonical Ordering 與 `initiator_id` 控制重複關係，並以 ID 升序的 2 向悲觀鎖與批次更新抑制矛盾狀態與解除遺漏。
- **Q: NPC 批次同步回合時，中間提交會導致鎖遺失嗎？**
  - **A:** [v1.8.6] 循環外只取得 NPC ID 清單，循環內為各 NPC 分別建立隔離交易並加上悲觀鎖。若發生例外，則以 `begin_nested()` 只回滾失敗部分，保留整體鎖與回合資訊。
- **Q: 拒絕交易時，惡意使用者能否篡改交易 ID 強制拒絕他人交易？已滅亡用戶的交易會留在市場中嗎？**
  - **A:** [v1.8.7] 已在 `trade_reject` 的 UPDATE 條件加入 `receiver_id == park.id`，只允許收件者本人拒絕。`trade_market()` 也會篩除 `Park.is_destroyed == False` 以外的提案。
- **Q: 慢速路徑執行期間，其他非同步請求扣除 AP 時，會因舊資料覆寫而複製 AP 嗎？**
  - **A:** [v1.8.8] 慢速路徑結尾會再次取得悲觀鎖並執行 `refresh`，再做最終 AP 減算，因此可抑制 Lost Update。 (audit_report_56.md [STATE-F029])
- **Q: NPC 戰鬥中若遇到 `ResourceClosedError` 等錯誤，會中斷同步迴圈或造成 AP、資源遺失嗎？**
  - **A:** [v1.8.9] 已將 NPC 戰鬥內的 `commit()` 改為 `flush()`，並保護巢狀 Savepoint。退還 AP 會在例外區段立即提交，過密處理前也會再次取得悲觀鎖並執行 `refresh`。
- **Q: NPC 攻擊時，會因鎖定順序衝突而發生死鎖或耗盡 DB 連線嗎？**
  - **A:** [v1.8.9] 已移除 `process_npc_turn()` 開頭的先行悲觀鎖，改由 `_sync_npc_turns()` 在基本回合完成後先行提交並釋放鎖。攻擊時的鎖只在 `execute_battle()` 內依 Canonical Ordering 取得，因此較不易產生死鎖。

### 🇨🇳 简体中文
- **Q: 仪表板和游戏操作同时执行时，会发生 Lost Update 吗？**
  - **A:** [v1.8.0] 保护模式下已应用悲观锁（`with_for_update()`）与数据同步（`refresh`），可降低并发请求覆盖数据的风险。
- **Q: 重新开始后会回到登录画面并出现无限重定向吗？**
  - **A:** [v1.8.0] 重新开始流程已整合为单一原子处理；若侦测到用户失去公园，系统会自动重建默认公园，降低循环风险。
- **Q: 多进程环境下会出现交易限制绕过或 NPC 重复执行回合吗？**
  - **A:** [v1.8.1] 已改用数据库层级的悲观锁（`with_for_update()`）配合 `turn_count` 同步防护，以维持跨进程的直线化执行。
- **Q: 用户攻击 NPC 时，资源会被覆盖，或在例外时出现不当复制吗？**
  - **A:** [v1.8.1] 已将 NPC 自然成长改为单一原子化 SQL `UPDATE`，以避免 `autoflush` 覆盖，并使整个 NPC 回合在单一交易内执行与回滚。
- **Q: 行动执行中如果因资源不足或验证失败而中断，先前扣除的 AP 会消失吗？**
  - **A:** [v1.8.2] 行动失败时，系统会启动补偿交易（`game_engine.refund_ap`），将已先行扣除的 AP 返还给玩家。
- **Q: 随着回合推进公园已灭亡时，还能继续行动或与其交易、战斗吗？**
  - **A:** [v1.8.3] 若 `consume_turn` 导致公园灭亡，行动会立即中止。交易与战斗在取得悲观锁后也会再次验证灭亡状态，以降低僵尸行动与 TOCTOU 风险。
- **Q: 对方公园被删除时，我提出的交易资源或派遣的密使会持续消失吗？**
  - **A:** [v1.8.4] 通过 `before_delete` 事件监听器，对方执行 `/restart` 导致交易或密使被级联删除时，系统会把待处理的托管资源与执行中的密使返还给发送方公园。
- **Q: 两个公园同时互送外交请求时，会产生重复关系或矛盾状态吗？**
  - **A:** [v1.8.5] 通过 `park_a_id < park_b_id` 的 Canonical Ordering 与 `initiator_id` 控制重复关系，并用 ID 升序的双向悲观锁和批量更新抑制矛盾状态与解除遗漏。
- **Q: NPC 批量同步回合时，中间提交会导致锁丢失吗？**
  - **A:** [v1.8.6] 循环外只获取 NPC ID 列表，循环内为各 NPC 分别建立隔离交易并加上悲观锁。若发生异常，则用 `begin_nested()` 只回滚失败部分，保留整体锁与回合信息。
- **Q: 拒绝交易时，恶意用户能否篡改交易 ID 强制拒绝他人交易？已灭亡用户的交易会留在市场中吗？**
  - **A:** [v1.8.7] 已在 `trade_reject` 的 UPDATE 条件中加入 `receiver_id == park.id`，只允许收件者本人拒绝。`trade_market()` 也会筛除 `Park.is_destroyed == False` 以外的提案。
- **Q: 慢速路径执行期间，其他异步请求扣除 AP 时，会因旧数据覆盖而复制 AP 吗？**
  - **A:** [v1.8.8] 慢速路径末尾会再次获取悲观锁并执行 `refresh`，再进行最终 AP 减算，因此可抑制 Lost Update。 (audit_report_56.md [STATE-F029])
- **Q: NPC 战斗中若遇到 `ResourceClosedError` 等错误，会中断同步循环或造成 AP、资源丢失吗？**
  - **A:** [v1.8.9] 已将 NPC 战斗内的 `commit()` 改为 `flush()`，并保护嵌套 Savepoint。返还 AP 会在异常区段立即提交，过密处理前也会再次获取悲观锁并执行 `refresh`。
- **Q: NPC 攻击时，会因锁定顺序冲突而发生死锁或耗尽 DB 连接吗？**
  - **A:** [v1.8.9] 已移除 `process_npc_turn()` 开头的先行悲观锁，改由 `_sync_npc_turns()` 在基本回合完成后先行提交并释放锁。攻击时的锁只在 `execute_battle()` 内依 Canonical Ordering 取得，因此较不易产生死锁。
