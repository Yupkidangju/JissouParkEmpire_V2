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
python run.py
# 또는 가상환경 외부에서 직접 기동:
venv/bin/python run.py
```

### 동시성 지원 매트릭스 (Concurrency Support Matrix)
본 프로젝트는 초경량 zero-setup 및 단일 서버 운영 환경을 기본으로 하여 SQLite를 채택하였으나, 다중 프로세스(Gunicorn) 다중 워커 프로덕션 환경의 동시성 안전성을 위해 설계되었습니다.

| 운영 조합 | 지원 여부 | 아키텍처 대응 및 완화 전략 |
|-----------|-----------|---------------------------|
| **SQLite + 단일 워커 (Single Worker)** | **공식 권장 (Supported)** | 개발 및 소형 호스팅에서 조건부 데이터 일관성(Consistency)이 보장됩니다. SQLite WAL 활성화 및 내부 sequential lock으로 동시 쓰기 정합성을 소화합니다. 다만 SQLite 환경에서 `with_for_update()`는 실제 DB 행 락(Row Lock)을 걸지 않는 무효(no-op) 상태이므로, Flask 개발 서버 구동 시 thread 1개와 단일 동시 쓰기 조건 하에서만 정합성이 온전히 유지됩니다. |
| **SQLite + 다중 워커 (Multi Worker)** | **제한 지원 (Accepted Risk / Limited)** | 다중 프로세스 간의 DB 쓰기 경쟁 시 `Database Locked` 가능성이 존재합니다. busy_timeout=5000을 강제 주입해 예외를 최소화하지만, 경합 발생은 감수해야 할 한계(Accepted Risk)로 정의합니다. (※ 상세 사양: 책임자 Eunho Lim / DAU 100명 미만 또는 초당 DB 쓰기 10회 미만 한정 수용 / Database Locked 주 3회 감지 시 PostgreSQL 즉각 전환 조건부 수용) |
| **PostgreSQL/MySQL + 다중 워커** | **공식 프로덕션 대상 (Target Production / Accepted Risk)** | 대규모 확장 및 다중 접속을 위한 최적 조합입니다. 본 프로젝트의 2중 ID 정렬(Canonical Order) 락 획득 설계와 2단계 트랜잭션 경계 분리 구조가 PostgreSQL/MySQL 등 네이티브 행 락(Row Lock)에서 안정적으로 상호 작용하여, 교착 상태(Deadlock) 발생 위험이 극도로 예방된 동시 처리를 지원하도록 설계되었습니다. <br>※ **Accepted Risk 상세 규격 (PostgreSQL/MySQL 실 DB row-lock/deadlock 미검증)**:<br>- **책임자(Owner)**: `Project Lead Architect / Eunho Lim`<br>- **수용 사유**: 현재 개발/테스트 인프라 제약으로 인해 실제 PostgreSQL/MySQL 인스턴스를 통한 다중 worker 부하 및 row-lock/deadlock E2E 검증은 수행하지 않았으며, ID Canonical Ordering 설계적 안전성만을 확보한 상태에서 운영 위험을 잠재적으로 수용함.<br>- **만료 조건**: 프로덕션 DB로 실제 PostgreSQL/MySQL 이주 완료 및 해당 DB 상에서 다중 스레드 부하 테스트/교착 검증 스위트를 최초로 수행 및 통과하는 시점.<br>- **재검토 조건**: 실제 RDBMS 프로덕션 이주 후 lock timeout 또는 deadlock 경보가 시스템 상에서 최초로 주 1회 이상 감지되는 시점. |

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
| **PostgreSQL/MySQL + Multi Worker** | **Target Production (Accepted Risk)** | Optimal combo for large-scale scaling and high-concurrency hosting. The 2-way ID-sorted (Canonical Order) locking and two-stage transaction separation integrate natively with row locks to strongly prevent deadlocks and support concurrency. <br>※ **Accepted Risk Specifications (PostgreSQL/MySQL Real Instance Unverified)**:<br>- **Owner**: `Project Lead Architect / Eunho Lim`<br>- **Reason**: Due to dev/test infrastructure constraints, E2E multi-worker load and row-lock/deadlock validation on real PostgreSQL/MySQL instances were not performed. Concurrency is designed on ID Canonical Ordering, but unverified real DB locking is accepted as a potential operational risk.<br>- **Expiry Condition**: Completion of production migration to real PostgreSQL/MySQL and successful completion of the first multi-threaded load/deadlock validation suite.<br>- **Recheck Condition**: First detection of any lock timeout or deadlock alarm >=1 time a week in production. |

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
| **SQLite + シングルワーカー (Single Worker)** | **公式推奨 (Supported)** | 開発および小規模ホスティングで条件付きの一貫性（Consistency）が保証されます。SQLite WALの有効化と内部的な順序ロックにより安全に処理されます。ただし、SQLite環境において `with_for_update()` は実際の行ロック（Row Lock）をかけない無効（no-op）状態であるため、Flask開発サーバーのthread 1つおよび単一同時書き込みの制限下でのみ整合性が維持されます。 |
| **SQLite + マルチワーカー (Multi Worker)** | **制限付きサポート (Accepted Risk / Limited)** | 複数プロセス間の同時書き込み競合時に `Database Locked` が発生する可能性があります。busy_timeout=5000 を注入して例外を最小限に抑えますが、高負荷時の競合は許容されるリスク（Accepted Risk）と定義します。（※詳細仕様：責任者 Eunho Lim / DAU 100人未満または秒間書き込み10回未満の制限的な許容 / Database Lockedが週3回以上検出された場合、PostgreSQLへ即時移行） |
| **PostgreSQL/MySQL + マルチワーカー** | **本番公式対象 (Target Production / Accepted Risk)** | 大規模スケーリングと高同時実行用の最適組合せです。本プロジェクトの2重ID整列（Canonical Order）悲観的ロック設計と2段階トランザクション境界分離構造が、PostgreSQL/MySQLなどのネイティブ行ロック（Row Lock）で強力に連動し、デッドロックを高度に防ぐ高性能な同時実行をサポートします。 <br>※ **Accepted Risk 詳細仕様 (PostgreSQL/MySQL 実DB row-lock/deadlock 未検証)**:<br>- **責任者(Owner)**: `Project Lead Architect / Eunho Lim`<br>- **受容理由**: 現在の開発/テストインフラの制約により、実際のPostgreSQL/MySQLインスタンスを使用したマルチワーカー負荷およびrow-lock/deadlockのE2E検証は行っておらず、ID Canonical Orderingによる設計的安全性のみを確保した状態で運用のリスクを潜在的に受容します。<br>- **満了条件**: 本番DBとして実際のPostgreSQL/MySQLへの移行が完了し、当該DB上でのマルチスレッド負荷テスト/デッドロック検証スイートを初めて実施および通過した時点。<br>- **再検討条件**: 実際のRDBMS本番移行後、システム上でlock timeoutまたはdeadlockのアラームが初めて週1回以上検出された時点。 |

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
| **SQLite + 單工作線程 (Single Worker)** | **官方推薦 (Supported)** | 在單線程與單寫入限制條件下，保證開發和小規模託管的一致性（Consistency）。併發寫入透過 SQLite WAL 和內部順序鎖安全處理。請注意，`with_for_update()` 在 SQLite 下為無效操作（no-op），不提供真實的原生行級鎖，因此僅在 Flask 開發伺服器單一執行緒與單一寫入限制下維持一致性。 |
| **SQLite + 多工作線程 (Multi Worker)** | **限制支援 (Accepted Risk / Limited)** | 在併發寫入競爭下可能會出現 `Database Locked` 錯誤。透過強制注入 `PRAGMA busy_timeout=5000` 來最小化異常，但高負載下的競爭被定義為可接受的風險（Accepted Risk）。（※詳細規格：負責人 Eunho Lim / DAU < 100 或每秒寫入 < 10 次限制接受 / 週偵測鎖錯誤 >= 3 次時即刻強制轉移至 PostgreSQL）。 |
| **PostgreSQL/MySQL + 多工作線程** | **官方生產目標 (Target Production / Accepted Risk)** | 大規模擴展和高併發託管的最佳組合。雙向 ID 排序（Canonical Order）悲觀鎖與兩階段事務邊界分離結構能與 PostgreSQL/MySQL 等原生行鎖（Row Lock）強力結合，高度預防死鎖的高性能併發。 <br>※ **Accepted Risk 詳細規格 (PostgreSQL/MySQL 實DB row-lock/deadlock 未驗證)**:<br>- **負責人(Owner)**: `Project Lead Architect / Eunho Lim`<br>- **接受理由**: 由於目前開發/測試基礎設施的限制，尚未通過實際的 PostgreSQL/MySQL 實例進行多工作線程負載及 row-lock/deadlock 的 E2E 驗證，在僅確保 ID Canonical Ordering 設計安全性的情況下，暫時接受潛在的運作風險。<br>- **滿期條件**: 完成將生產環境實際轉移至 PostgreSQL/MySQL，並首次在該資料庫上執行並通過多線程負載測試/死鎖驗證套件。<br>- **重新評估條件**: 實際轉移至 RDBMS 生產環境後，系統首次偵測到 lock timeout 或 deadlock 警報達到每週 1 次以上。 |

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
| **SQLite + 单工作线程 (Single Worker)** | **官方推荐 (Supported)** | 在单线程与单写入限制条件下，保证开发和小规模托管的一致性（Consistency）。并发写入通过 SQLite WAL 和内部顺序锁安全处理。请注意，`with_for_update()` 在 SQLite 下为无效操作（no-op），不提供真实的原生行级锁。 |
| **SQLite + 多工作工作线程 (Multi Worker)** | **限制支持 (Accepted Risk / Limited)** | 在并发写入竞争下可能会出现 `Database Locked` 错误。通过强制注入 busy_timeout=5000 来最小化异常，但高负载下的竞争被定义为可接受的风险（Accepted Risk）。（※详细规格：负责人 Eunho Lim / DAU < 100 或每秒写入 < 10 次限制接受 / 周侦测锁错误 >= 3 次时即刻强制转移至 PostgreSQL）。 |
| **PostgreSQL/MySQL + 多工作线程** | **官方生产目标 (Target Production / Accepted Risk)** | 大规模扩展和高并发托管的最佳组合。双向 ID 排序（Canonical Order）悲观锁与两阶段事务边界分离结构能与 PostgreSQL/MySQL 等原生行锁（Row Lock）强力结合，高度预防死锁的高性能并发。 <br>※ **Accepted Risk 详细规格 (PostgreSQL/MySQL 实DB row-lock/deadlock 未验证)**:<br>- **负责人(Owner)**: `Project Lead Architect / Eunho Lim`<br>- **接受理由**: 由于目前开发/测试基础设施的限制，尚未通过实际的 PostgreSQL/MySQL 实例进行多工作线程负载及 row-lock/deadlock 的 E2E 验证，在仅确保 ID Canonical Ordering 设计安全性的情况下，暂时接受潜在的运作风险。<br>- **满期条件**: 完成将生产环境实际转移至 PostgreSQL/MySQL, 并首次在该数据库上运行并通过多线程负载测试/死锁验证套件。<br>- **重新评估条件**: 实际转移至 RDBMS 生产环境后，系统首次侦测到 lock timeout 或 deadlock 警报达到每周 1 次以上。 |

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
  - **A:** [v1.8.0] 보호 모드 자원 보충(`check_and_enter_protection`) 시 비관적 락(`with_for_update()`)과 데이터 강제 동기화(`refresh`)가 적용되어 동시 다발적인 요청 시에도 데이터 훼손이 발생하지 않습니다.
- **Q: 게임오버 후 재시작 시 로그인 화면으로 튕기며 무한 리다이렉트가 일어나나요?**
  - **A:** [v1.8.0] 재시작 트랜잭션이 원자적으로 통합되었으며, 공원이 유실된 유저에게는 루트 및 로그인 진입 시 자동으로 기본 공원이 즉시 복구 재생성되는 방어막이 가동되어 무한 루프가 발생하지 않습니다.
- **Q: 다중 프로세스(Gunicorn 멀티 워커) 환경에서 교역 한도 우회나 NPC 중복 턴(NPC Stampede)이 발생하나요?**
  - **A:** [v1.8.1] 기존 파이썬 스레드 락(`threading.Lock`)을 DB 비관적 락(`with_for_update()`) 및 `turn_count` 선행 동기화 가드로 전면 대체하여 프로세스 장벽을 넘는 수준 높은 동시성 직렬화를 보장합니다.
- **Q: 플레이어 공격 시 NPC 자원 덮어쓰기(Lost Update) 및 NPC 턴 예외 시 자원 증식 버그가 있나요?**
  - **A:** [v1.8.1] NPC 자연 성장을 단일 원자적 `UPDATE`로 전환하여 `autoflush` Lost Update를 방어하였고, 범용 엔진 기능에 `commit=False` 제어권을 인입해 NPC 턴 전체가 원자적 단일 트랜잭션 내에서 처리 및 롤백되도록 안전 조치하였습니다.
- **Q: 행동 실행 도중 자원 부족이나 유효성 검사 실패 등으로 실패했을 때, 선행 차감된 AP(행동포인트)가 증발하나요?**
  - **A:** [v1.8.2] 행동이 실패(`not success`)할 경우, 이미 `consume_turn`에 의해 선행 커밋된 AP를 안전하게 플레이어에게 돌려주는 공용 보상 트랜잭션(`game_engine.refund_ap`)이 안정적으로 가동되므로 AP가 허공으로 소멸되는 자원 누수(AP Leakage) 현상이 발생하지 않습니다.
- **Q: 턴이 지나면서 공원이 멸망한 상태에서 행동을 한 번 더 하거나, 멸망한 공원과 교역/전투가 일어날 수 있나요?**
  - **A:** [v1.8.3] `consume_turn`에서 턴 소비로 인해 공원이 멸망하면 즉시 조기 기각되고 차단되며, 교역 수락(`trade_accept`) 및 전투(`execute_battle`)에서도 비관적 락을 획득한 직후 상대방의 멸망 상태를 재검증하므로 좀비 행동(Zombie Action) 및 TOCTOU 결함이 안전하게 차단됩니다.
- **Q: 상대방 공원이 삭제(재시작)될 때, 내가 제안했던 교역 자원이나 파견된 밀사(성체실장)가 영구히 증발하나요?**
  - **A:** [v1.8.4] 데이터베이스 삭제 전(`before_delete`) 이벤트 리스너를 도입하여, 상대방이 `/restart` 등으로 공원을 삭제해 교역이나 밀사가 Cascade Delete될 때, 대기 중이던 에스크로 자원 및 파견 중인 성체실장을 자동으로 발신자 공원에 되돌려줍니다(cap 한도 적용). 자원 유실(Resource Leakage)이 근본적으로 차단됩니다.
- **Q: 두 공원이 동시에 서로에게 외교 요청(동맹/적대)을 보낼 때, 중복 관계가 생성되거나 모순된 상태(동맹이자 적대)가 발생하나요?**
  - **A:** [v1.8.5] 두 공원 간의 외교 관계 저장 시 항상 `park_a_id < park_b_id`를 만족하는 Canonical Ordering 및 `initiator_id` 컬럼을 적용하여 Unique 제약이 안전하게 중복 생성을 막아줍니다. 또한, 외교 처리 시 ID 오름차순의 2중 비관적 락을 일괄 획득하여 교사 데드락을 원천 예방하고, 관계 변경 시 벌크 쿼리(`update()`)를 통한 일괄 상태 해제를 가동하여 "동맹이자 적대"라는 모순 상태와 상태 해제 누락 현상을 안전하게 방지하고 복구합니다.
- **Q: NPC 일괄 턴 동기화 시 중간 커밋으로 인해 다른 플레이어가 개입하여 락이 유실되거나 Lost Update가 발생하나요?**
  - **A:** [v1.8.6] 루프 외부에서 모든 NPC를 한 번에 락킹한 뒤 루프 내부에서 커밋하던 구조적 한계를 극복했습니다. 루프 외부에서는 오직 ID 목록만 추출하고, 루프 내부에서 **개별 트랜잭션 단위로 각 NPC를 조회하고 비관적 락(`with_for_update()`)**을 확보해 격리 처리합니다. 또한, NPC 행동 중 예외가 발생하더라도 **Nested Transaction (Savepoint, `begin_nested()`)**을 기동하여 전체 비관적 락 유실 및 턴 정보 롤백 없이 안전하게 격리 복구되도록 조치했습니다. 밀사 사보타주 시에도 2-Way Lock을 걸어 계산 격차(TOCTOU)를 고도 예방했습니다.
- **Q: 교역 거절 시 악의적인 유저가 임의의 교역 ID를 변조하여 타인의 프라이빗 교역을 강제로 거절(IDOR)할 수 있나요? 또한 멸망한 유저의 교역(Zombie Trades)이 시장에 지속 노출되나요?**
  - **A:** [v1.8.7] 교역 거절(`trade_reject`) API의 원자적 UPDATE 조건식에 `receiver_id == park.id` 가드 조건을 추가하여 오직 제안을 받은 본인만 거절할 수 있도록 인가(Authorization)를 강제해 IDOR 취약점을 근본 차단했습니다. 또한, 멸망한 유저의 교역 제안이 시장에 지속 노출되는 좀비 거래 현상을 방지하기 위해 `trade_market()` 쿼리 단계에서 `Park` 모델을 JOIN하여 발송자가 살아있는(`is_destroyed == False`) 교역 제안만 동적으로 걸러서 보여주도록 정화했습니다.
- **Q: 슬로우 패스(턴 소비 및 NPC 동기 턴 진행) 실행 도중, 다른 비동기 요청이 AP를 차감할 때 메모리 덮어쓰기(Lost Update)로 AP가 복제(무상 사용)되나요?**
  - **A:** [v1.8.8] `consume_turn()` 슬로우 패스에서 `process_turn()` 및 `_sync_npc_turns()`를 기동하는 도중 플레이어 락이 해제되어 비동기 다중 요청(패스트 패스)이 AP를 차감하여 성공하더라도, 슬로우 패스 끝단에서 **다시 플레이어 공원 락을 획득하고 최신 상태로 새로고침(`refresh`)** 한 뒤 최종 AP 감산을 진행하도록 보강하여 AP 복제(Lost Update) 결함을 성공적으로 해결했습니다. (audit_report_56.md [STATE-F029])
- **Q: NPC 턴 진행 중 전투 발생 시 `ResourceClosedError` 등으로 턴 동기화 루프가 깨지거나 무한 루프가 발생하나요? 또한 행동 실패 시 환불된 AP가 유실되는 현상이 있나요? 밀사 귀환 후 overcrowding 처리 시 Lost Update로 자원이 소멸/복제될 수 있나요?**
  - **A:** [v1.8.9] 세부 사항을 성공적으로 해결했습니다. NPC의 전투 기동 내부 `commit()`을 `flush()`로 변경해 중첩 세이브포인트를 지키고 2중 롤백 예외 방어로 안정을 확보했습니다. 환불 `refund_ap` 작동 후 라우터 단에서 즉각 명시적 `db.session.commit()`을 수행해 롤백 유실을 안정적으로 막았으며, 밀사 임무 처리(`_process_spy_missions`) 끝단에서 과밀도 처리 전 다시 한번 플레이어 공원의 `with_for_update()` 비관적 락을 걸고 `refresh`를 실행하여 concurrent 다중 요청에 의한 데이터 덮어쓰기(Lost Update)를 안전하게 차단했습니다.
- **Q: NPC가 플레이어 또는 다른 공원을 공격할 때 락 획득 순서가 꼬여 교착 상태(Deadlock)가 발생하고 DB 커넥션이 고갈되나요?**
  - **A:** [v1.8.9] 설계적으로 교착 상태 취약점`[DEADLOCK-F005]`을 고도 예방했습니다. 기존 `process_npc_turn()` 시작 부분에서 무조건적으로 대상 NPC 공원 레코드를 선점 락킹하던 비관적 락(`with_for_update()`)을 제거하고 단순 리프레시만 전개하는 동시에, 상위 턴 동기화 스케줄러 `_sync_npc_turns()`에서 NPC 기본 턴 처리(`process_turn`) 완료 즉시 `db.session.commit()`을 강제하여 선점 락을 해제한 후 `process_npc_turn()`을 독립된 트랜잭션으로 기동하는 **2단계 트랜잭션 경계 분리 구조**를 적용했습니다. 이로 인해 NPC가 공격 행동을 취할 때 오직 `execute_battle()` 내부에서만 두 공원의 락을 Canonical Ordering(ID 오름차순 정렬) 순으로 안전하게 동시 획득하도록 보장함으로써 상호 락 대기 충돌에 의한 데드락 및 DB 커넥션 풀 고갈 결함 발생 위험을 극도로 예방했습니다 (단, 실제 PostgreSQL/MySQL 인스턴스 환경의 E2E 및 부하 검증은 Accepted Risk 상태로 유지됩니다).

### 🇺🇸 English
- **Q: Does concurrent Lost Update occur during dashboard and game actions?**
  - **A:** [v1.8.0] A pessimistic lock (`with_for_update()`) and data synchronization (`refresh`) are enforced during protection mode bailout, ensuring no data loss under concurrent actions.
- **Q: Does an infinite redirect occur after clicking restart and getting bounced to login?**
  - **A:** [v1.8.0] Restart is now atomic, and any authenticated user with a missing park will automatically have a default park reconstructed instantly, preventing redirect loops.
- **Q: Does trade limit bypass or duplicated NPC turns (NPC Stampede) occur in a multi-process (Gunicorn) environment?**
  - **A:** [v1.8.1] Thread locks (`threading.Lock`) have been replaced with database-level pessimistic locks (`with_for_update()`) combined with sequential ID locking and a `turn_count` synchronization guard, strongly preventing process-safe serialization issues and minimizing concurrency conflicts.
- **Q: Is there any issue with overwritten NPC resources (Lost Update) on player attacks or infinite resource bugs on NPC turn exceptions?**
  - **A:** [v1.8.1] NPC passive growth is now an atomic SQL `UPDATE` to prevent `autoflush` Lost Updates, and intermediate commits are suppressed (`commit=False`) during NPC actions, ensuring the entire NPC turn handles execution and rollback inside a single atomic transaction.
- **Q: Do prior action points (AP) evaporate when an action fails due to insufficient resources or validation failure during execution?**
  - **A:** [v1.8.2] In case of action failure (`not success`), a compensating transaction (`game_engine.refund_ap`) is triggered to safely return the pre-deducted AP to the player, eliminating any potential AP leakage or ghost deduction.
- **Q: Is it possible for a player to take a zombie action after their park is destroyed, or trade/fight with an already destroyed park?**
  - **A:** [v1.8.3] If a park gets destroyed due to turn progression inside `consume_turn`, the action is instantly aborted. Furthermore, `trade_accept` and `execute_battle` double-check the destruction state right after acquiring pessimistic locks, highly blocking zombie actions and TOCTOU flaws.
- **Q: When the opponent's park is deleted (restarted), do my proposed trade resources or dispatched spy units (adults) evaporate permanently?**
  - **A:** [v1.8.4] By introducing database-level `before_delete` event listeners, if a trade offer or spy mission is cascade-deleted due to the opponent executing a `/restart`, any pending escrow resources and active spy units are automatically refunded to the sender (applying cap clamping). Resource leakage is highly prevented.
- **Q: When two parks send diplomatic requests (alliance/hostility) to each other simultaneously, do duplicate relationships or contradictory states (both allied and hostile) occur?**
  - **A:** [v1.8.5] By enforcing Canonical Ordering (`park_a_id < park_b_id`) and utilizing the `initiator_id` column when saving diplomatic relations, the database UniqueConstraint strongly blocks duplicate records. Additionally, we enforce ID-sorted 2-Way pessimistic locking to highly prevent deadlocks, and use bulk updates (`update()`) to dissolve all active/pending duplicate relations between the two parks simultaneously, ensuring no contradictory states occur.
- **Q: During concurrent NPC turn synchronizations, do intermediate commits cause lock loss or Lost Updates?**
  - **A:** [v1.8.6] Yes, we resolved the structural limitation where locking all NPCs at once resulted in early lock releases inside the loop due to intermediate commits. We now query only NPC IDs outside the loop, and inside the loop, we query and acquire a pessimistic lock (`with_for_update()`) on each NPC park in **individual isolated transactions**. Additionally, if an action fails, a **Nested Transaction (Savepoint, `begin_nested()`)** is utilized to roll back only the failed action, protecting the overall pessimistic lock and preventing turn count rollbacks (Stampede). Spy sabotage is also guarded with a 2-Way Lock to eliminate the TOCTOU calculation window.
- **Q: When rejecting a trade, can a malicious user tamper with the trade ID to force-reject someone else's private trade (IDOR)? Also, do trade offers from destroyed users (Zombie Trades) persist in the market?**
  - **A:** [v1.8.7] We strongly mitigated the IDOR vulnerability by adding the `receiver_id == park.id` guard condition to the atomic UPDATE query of the `trade_reject` API, ensuring that only the designated recipient can reject private trade offers. Furthermore, to prevent "Zombie Trades" from persisting in the market, we modified the `trade_market()` query to JOIN the `Park` model and dynamically filter out pending trade offers from senders who have already been destroyed (`is_destroyed == False`).
- **Q: During the slow-path (turn progression & NPC synchronization), if concurrent asynchronous requests deduct AP, does AP duplication (Lost Update) occur due to stale memory overwrites?**
  - **A:** [v1.8.8] We highly resolved the AP duplication (Lost Update) flaw. Even if concurrent fast-path requests successfully deduct AP during the lock-free synchronization gap of the slow-path, the end of the slow-path **re-acquires the player's pessimistic lock and enforces a database `refresh`** before performing the final AP subtraction, ensuring atomic and up-to-date computations. (audit_report_56.md [STATE-F029])
- **Q: During NPC turns, does battle cause `ResourceClosedError` disrupting turn sync or infinite loop? Also, is there any loss of refunded AP on action failures, or Lost Update causing resource duplication/loss when resolving overcrowding after spy return?**
  - **A:** [v1.8.9] Fully resolved. NPC battle commit has been changed to `flush()` to preserve nested savepoints, protected by a double-rollback exception guard. Refunded AP is permanently stored by executing explicit `db.session.commit()` directly at the router exception block. Finally, before resolving overcrowding in `_process_spy_missions`, we acquire a `with_for_update()` pessimistic lock and perform `refresh` on the player park, strongly preventing concurrent requests from overwriting data (Lost Update).
- **Q: Does a lock order inversion occur when an NPC attacks a player or another park, causing a deadlock and database connection exhaustion?**
  - **A:** [v1.8.9] The deadlock vulnerability `[DEADLOCK-F005]` has been designed to be highly prevented. We have removed the pessimistic lock (`with_for_update()`) that was pre-acquired at the start of `process_npc_turn()`, replacing it with a simple `refresh`. Concurrently, we introduced a **two-stage transaction boundary separation** in the synchronization scheduler `_sync_npc_turns()`, which forces `db.session.commit()` immediately after finishing the basic NPC turn processing (`process_turn`) to release any pre-acquired locks before spawning the independent `process_npc_turn()` AI action. As a result, when an NPC initiates an attack, locks for both parks are acquired concurrently only inside `execute_battle()` according to Canonical Ordering (sorted by ID in ascending order). This strongly prevents lock order inversion deadlock conflicts and DB connection pool exhaustion (Note: E2E concurrency validation on real PostgreSQL/MySQL instances remains an Accepted Risk).

### 🇯🇵 日本語
- **Q: ダッシュボードとゲーム行動の間に同時実行によるLost Updateが発生しますか？**
  - **A:** [v1.8.0] 保護モード起動時に悲観的ロック（`with_for_update()`）とデータ同期（`refresh`）が強制適用され、データの破損を防ぎます。
- **Q: 再起動後にログイン画面へ飛ばされ、無限リダイレクトが発生しますか？**
  - **A:** [v1.8.0] 再起動処理が単一トランザクションに統合され、公園を失ったユーザーには自動回復システムが作動してデフォルト公園を即時再生成し、ループを防ぎます。
- **Q: 多重プロセス（Gunicornマルチワーカー）環境で交易制限の迂回やNPCの重複ターン（NPC Stampede）が発生しますか？**
  - **A:** [v1.8.1] スレッドロック（`threading.Lock`）を廃止し、DBレベルの悲観的ロック（`with_for_update()`）と`turn_count`同期ガードに移行することで、プロセス境界を越えた完全な直列化を保証します。
- **Q: プレイヤーの攻撃時にNPCの資源が上書き（Lost Update）されたり、例外発生時に資源が増殖するバ그はありますか？**
  - **A:** [v1.8.1] NPCの自然成長を単一の原子的な`UPDATE`に変換して`autoflush`による上書きを防御し、NPCターン全体が単一トランザクション内で実行およびロールバックされるよう安全対策を講じました。
- **Q: 行動実行中に資源不足やバリデーション失敗で失敗した場合、AP（行動ポイント）は消滅しますか？**
  - **A:** [v1.8.2] アクションが失敗した場合、既に先行コミットされたAPをプレイヤーに安全に返還する補償トランザクション（`game_engine.refund_ap`）が完全に稼働するため、APの消失は発生しません。
- **Q: ターン進行により公園が滅亡した状態でさらに行動をとったり、滅亡した公園と交易や戦闘を行うことは可能ですか？**
  - **A:** [v1.8.3] `consume_turn`のターン消費によって公園が滅亡した場合、アクションは即座に中断されブロックされます。また、交易や戦闘でも悲観的ロック取得直後に相手の滅亡状態を再検証するため、ゾンビ行動やTOCTOUの脆弱性は完全に排除されています。
- **Q: 相手の公園が削除（再起動）される際、自分が提案していた交易資源や派遣した密使（成体実装）が永久に消失しますか？**
  - **A:** [v1.8.4] データベースの `before_delete` イベントリスナーを導入することで、相手が `/restart` などで公園を削除し、交易や密使が連鎖削除（Cascade Delete）される際に、待機中のエスクロー資源や派遣中の成体実装を自動的に送信者の公園に返還します（Cap上限適用）。
- **Q: 2つの公園が同時にお互いに外交要請（同盟/敵対）を送る際、重複した関係が生成されたり、矛盾した状態（同盟かつ敵対）が発生しますか？**
  - **A:** [v1.8.5] 外交関係の保存時に常に `park_a_id < park_b_id` を満たす Canonical Ordering および `initiator_id` カラムを適用することで、データベースの Unique 制約が重複生成を完璧にブロックします。また、外交処理時にID昇順の2重悲観的ロックを一括取得してデッドロックを未然に防ぎ、関係変更時にはバルククエリ（`update()`）による一括状態解除を稼働させて、「同盟かつ敵対」という矛盾した状態や解除漏れを完全に排除します。
- **Q: NPCの一括ターン同期時、中間コミットによって他のプレイヤーが介入し、ロックが紛失したりLost Updateが発生しますか？**
  - **A:** [v1.8.6] ループ外部で全NPCを一括ロックしてからループ内でコミットする構造的な限界を克服しました。ループ外部ではIDリストのみを抽出し、ループ内部で**個別トランザクション単位で各NPCを検索して悲観的ロック（`with_for_update()`）**を確保することで隔離処理します。また、NPCの行動中に例外が発生した場合でも、**入れ子になったトランザクション（Savepoint, `begin_nested()`）**を起動し、全体悲観的ロックの紛失やターン情報のロールバックを起こすことなく安全に隔離・復旧するよう措置しました。密使のサボタージュ時にも2-Way Lockをかけて計算の乖離（TOCTOU）を完全に封鎖しました。
- **Q: 交易の拒否（Reject）時に、悪意のあるユーザーが任意の取引IDを改ざんして他人のプライベート取引を強制的に拒否（IDOR）できますか？また、滅亡したユーザーの取引（Zombie Trades）が市場に表示され続けますか？**
  - **A:** [v1.8.7] 交易拒否（`trade_reject`）APIの原子的なUPDATE条件式に `receiver_id == park.id` ガード条件を追加し、提案を受け取った本人だけが拒否できるように認可（Authorization）を強制することで、IDOR脆弱性を根本的に遮断しました。また、滅亡したユーザーの交易提案が市場に表示され続けるゾンビ取引現象を防ぐため、`trade_market()` クエリ段階で `Park` モデルをJOINし、送信者が生存している（`is_destroyed == False`）交易提案のみを動的に絞り込んで表示するよう浄化しました。
- **Q: スローパス（ターン消費とNPC同期ターン進行）実行中に、他の非同期リクエストがAPを差し引く際、メモリの上書き（Lost Update）によりAPが複製（タダ乗り）されますか？**
  - **A:** [v1.8.8] `consume_turn()` のスローパスで `process_turn()` や `_sync_npc_turns()` を実行する間にプレイヤーロックが解除され、非同期多重リクエスト（ファストパス）がAPを正常に差し引いたとしても、スローパスの最終段階で**再度プレイヤーの悲観적ロックを取得し、最新データでリフレッシュ（`refresh`）**してから最終的なAP減算を行うよう補強することで、AP複製（Lost Update）脆弱性を完璧に解決しました。 (audit_report_56.md [STATE-F029])
- **Q: NPCのターン進行中に戦闘が発生した際、`ResourceClosedError`などによってターン同期ループが崩壊したり無限ループになりますか？また行動失敗時に返還されたAPが消失したり、密使帰還後の過密処理時にLost Updateで資源が消失・複製される現象はありますか？**
  - **A:** [v1.8.9] すべて解決しました。NPC戦闘内部의 `commit()`を`flush()`に置換して入れ子になったセーブポイントを保護し、2重ロールバック例外ガードを適用しました。返還されたAPはルーターの例外ブロックで即座に明示的な`db.session.commit()`を実行しロールバック消失を完全に遮断しました。さらに、`_process_spy_missions`での過密処理前にプレイヤーの公園に対して`with_for_update()`悲観적ロックを取得し`refresh`を行うことで、並行リクエストによるデータの書き換え（Lost Update）を完璧に防ぎました。
- **Q: NPCがプレイヤーまたは他の公園を攻撃する際、ロックの取得順序が逆転してデッドロック（Deadlock）が発生し、DB接続が枯渇しますか？**
  - **A:** [v1.8.9] デッドロックの脆弱性`[DEADLOCK-F005]`を完全に解決しました。従来の `process_npc_turn()` 開始時に無条件で対象NPC公園レコードを占有ロックしていた悲観的ロック（`with_for_update()`）を完全に排除して単純なリフレッシュのみを実行するように変更すると同時に、上位のターン同期スケジューラ `_sync_npc_turns()` でNPCの基本ターン処理（`process_turn`）完了直後に `db.session.commit()` を強制して先行ロックを完全に解放した後、`process_npc_turn()` を独立したトランザクションとして起動する**2段階トランザクション境界分離構造**を電撃適用しました。これにより、NPC가攻撃行動を行う際、`execute_battle()` 内部でのみ両公園のロックを Canonical Ordering（ID昇順整列）に沿って安全に同時取得するため、相互のロック待機衝突によるデッドロックやDBコネクションプールの枯渇懸念が完全に遮断されます。

### 🇹🇼 繁體中文
- **Q: 儀表板與遊戲行動之間會因同時執行而導致 Lost Update 嗎？**
  - **A:** [v1.8.0] 保護模式啟用時已強制套用悲觀鎖（`with_for_update()`）與資料同步（`refresh`），確保併發請求下資料不被覆蓋。
- **Q: 遊戲結束重新開始後，是否會跳轉至登入畫面並產生無限重導向？**
  - **A:** [v1.8.0] 重新開始事務已改為單一原子化處理，且若偵測到用戶遺失公園，系統將自動即時重建預設公園，杜絕無限循環。
- **Q: 在多進程環境下，是否會產生交易限制規避或 NPC 重複執行輪次（NPC Stampede）？**
  - **A:** [v1.8.1] 已全面將執行緒鎖（`threading.Lock`）替換為資料庫層級的悲觀鎖（`with_for_update()`）並結合 `turn_count` 同步防護，保證超越進程邊界的完整事務序列化。
- **Q: 用戶攻擊 NPC 時是否存在資源被覆蓋（Lost Update）或 NPC 輪次例外時產生資源無效複製的漏洞？**
  - **A:** [v1.8.1] 已將 NPC 自然成長轉換為單一原子化 SQL `UPDATE` 以防止 `autoflush` 覆蓋，確保整個 NPC 輪次在單一原子化事務內安全執行與回滾。
- **Q: 行動執行過程中若因資源不足或驗證失敗而中斷，先前扣除的 AP（行動點數）會消失嗎？**
  - **A:** [v1.8.2] 當行動失敗時，系統會自動啟動補償事務（`game_engine.refund_ap`），將已由 `consume_turn` 先行扣除的 AP 安全地退還給玩家，有效防範 AP 資源永久流失（AP Leakage）的問題。
- **Q: 隨著輪次推進而導致公園已滅亡時，還能再執行行動嗎？是否會與已滅亡的公園發生交易或戰鬥？**
  - **A:** [v1.8.3] 若因 `consume_turn` 中的輪次消耗導致公園滅亡，行動會被立即中止並攔截。此外，交易接受與戰鬥在取得悲觀鎖後，亦會即時重新驗證雙方的滅亡狀態，從而完全杜絕殭屍行動（Zombie Action）與 TOCTOU 漏洞。
- **Q: 當對方公園被刪除（重新開始）時，我所提議的交易資源或派遣的密使（成體實裝）會永久消失嗎？**
  - **A:** [v1.8.4] 通過引入資料庫層級的 `before_delete` 事件監聽器，當對方執行 `/restart` 導致交易或密使被級聯刪除（Cascade Delete）時，系統會自動將待處理的託管資源及執行中的密使返還給發送方公園（適用容量上限限制），從根本上杜絕了資源流失（Leakage）問題。
- **Q: 當兩個公園同時向對方發送外交請求（結盟/敵對）時，是否會產生重複的關係或矛盾的狀態（既是盟友又是敵人）？**
  - **A:** [v1.8.5] 通過在儲存外交關係時強制執行 Canonical Ordering（`park_a_id < park_b_id`）並引入 `initiator_id` 欄位，資料庫的 UniqueConstraint 能高度預防重複關係的生成。此外，我們採用按 ID 排序的 2 向悲觀鎖以高度預防死鎖，並使用批量更新（`update()`）一併解除兩公園間所有 active/pending 的重複關係，確保不會出現矛盾狀態或解除遺漏。
- **Q: 在 NPC 輪次同步過程中，中間提交（Commit）是否會導致鎖遺失或產生 Lost Update？**
  - **A:** [v1.8.6] 我們解決了在循環外部一次性鎖定所有 NPC、並在循環內部執行提交時所產生的過早釋放鎖的結構性缺陷。現在，我們在循環外部僅查詢 NPC ID 列表，並在循環內部採用**獨立隔離的事務**對每個 NPC 進行悲觀鎖定（`with_for_update()`）。此外，若 NPC 的某項行動失敗拋出異常，系統將啟動**嵌套事務（Nested Transaction / Savepoint, `begin_nested()`）**僅回滾該失敗行動，從而保護整體的悲觀鎖並避免輪次計數回滾（防止 Stampede 發生）。密使破壞行動也套用了 2 向鎖以高度預防 TOCTOU 計算誤差。
- **Q: 在拒絕交易時，惡意用戶是否能篡改交易 ID 以強制拒絕他人的私密交易（IDOR）？此外，已滅亡用戶的交易（Zombie Trades）是否會持續顯示在市場中？**
  - **A:** [v1.8.7] 我们在交易拒绝（`trade_reject`）API 的原子化 UPDATE 条件中新增了 `receiver_id == park.id` 防护条件，强制要求只有收到提议的本人才能拒绝交易，有效防范了 IDOR 权限越权漏洞。同时，为防止已灭亡用户的交易提议持续滞留在 market 中（殭屍交易），我们修改了 `trade_market()` 查詢，在 SQL 階段 JOIN `Park` 模型，僅動態篩選出發送方依然生存（`is_destroyed == False`）的交易提議進行顯示。
- **Q: 在慢速路徑（消耗輪次與 NPC 輪次同步）執行期間，若其他非同步請求扣除 AP，是否會因過期記憶體覆寫（Lost Update）而導致 AP 複製（免費使用）？**
  - **A:** [v1.8.8] 我們已高度緩解了 AP 複製（Lost Update）缺陷。即使在慢速路徑的無鎖同步間隙期間，併發的快速路徑請求成功扣成了 AP，慢速路徑的末端也會**重新取得玩家公園的悲觀鎖並強制執行 `refresh` 資料刷新**，隨後才進行最終的 AP 減算，從而確保了資料的高度一致性與原子性。 (audit_report_56.md [STATE-F029])
- **Q: 在 NPC 輪次進行中發生戰鬥時，會因 `ResourceClosedError` 等錯誤導致輪次同步中斷或陷入無限循環嗎？另外，行動失敗時退還的 AP 會流失嗎？或是密使歸還後的過密處理時會因 Lost Update 造成資源消失或複製嗎？**
  - **A:** [v1.8.9] 已高度缓解。NPC 战斗内部的 `commit()` 已被替换为 `flush()` 以保护嵌套的 Savepoint，并采用双重回滚异常防御。退还的 AP 在路由异常区段内会立即执行显式的 `db.session.commit()`，防止回滚流失。最后，在 `_process_spy_missions` 的过密处理前，系统会对玩家公园再次获取 `with_for_update()` 悲观锁并执行 `refresh`，高度预防并发请求对数据的覆盖（Lost Update）。
- **Q: 當 NPC 攻擊玩家或其他公園時，是否會因鎖定取得順序衝突而導致死鎖（Deadlock）並耗盡 DB 連線？**
  - **A:** [v1.8.9] 已高度防範死鎖漏洞 `[DEADLOCK-F005]`。我們已永久移除了在 `process_npc_turn()` 開始時無條件先行取得的悲觀鎖（`with_for_update()`），改為僅進行單純刷新（`refresh`），同時在上位輪次同步調度器 `_sync_npc_turns()` 中，NPC基本輪次處理（`process_turn`）完成後立即強制執行 `db.session.commit()` 以完全釋放先行鎖，隨後將 `process_npc_turn()` 作為獨立事務啟動，全方位採用了**兩階段事務邊界分離結構**。因此，當 NPC 發動攻擊時，兩個公園的鎖僅會在 `execute_battle()` 內部依據 Canonical Ordering（按 ID 升序排序）安全地同時取得。這高度預防了因相互鎖等待衝突導致的死鎖及資料庫連線池枯竭的問題。

### 🇨🇳 简体中文
- **Q: 仪表板与游戏行动之间会因同时执行而导致 Lost Update 吗？**
  - **A:** [v1.8.0] 保护模式启用时已强制套用悲观锁（`with_for_update()`）与数据同步（`refresh`），确保并发请求下数据不被覆盖。
- **Q: 游戏结束重新开始后，是否会跳转至登录画面并产生无限重定向？**
  - **A:** [v1.8.0] 重新开始事务已改为单一原子化处理，且若侦测到用户遗失公园，系统将自动即时重建默认公园，杜绝无限循环。
- **Q: 在多进程环境下，是否会产生交易限制规避或 NPC 重复执行轮次（NPC Stampede）？**
  - **A:** [v1.8.1] 已全面将线程锁（`threading.Lock`）替换为数据库层级的悲观锁（`with_for_update()`）并结合 `turn_count` 同步防护，保证超越进程边界的完整事务序列化。
- **Q: 用户攻击 NPC 时是否存在资源被覆盖（Lost Update） 或 NPC 轮次例外时产生资源无效复制的漏洞？**
  - **A:** [v1.8.1] 已将 NPC 自然成长转换为单一原子化 SQL `UPDATE` 以防止 `autoflush` 覆盖，确保整个 NPC 轮次在单一原子化事务内安全执行与回滚。
- **Q: 行动执行过程中若因资源不足或验证失败而中断，先前扣除的 AP（行动点数）会消失吗？**
  - **A:** [v1.8.2] 当行动失败时，系统会自动启动补偿事务（`game_engine.refund_ap`），将已由 `consume_turn` 先行扣除的 AP 安全地退还给玩家，有效防范 AP 资源永久流失（AP Leakage）的问题。
- **Q: 随着轮次推进而导致公园已灭亡时，还能再执行行动吗？是否会与已灭亡的公园发生交易或战斗？**
  - **A:** [v1.8.3] 若因 `consume_turn` 中的轮次消耗导致公园灭亡，行动会被立即中止并拦截。此外，交易接受和战斗在取得悲观锁后，亦会即时重新验证双方的灭亡状态，从而高度防范僵尸行动（Zombie Action）与 TOCTOU 漏洞。
- **Q: 当对方公园被删除（重新开始）时，我所提议的交易资源或派遣的密使（成体实装）会永久消失吗？**
  - **A:** [v1.8.4] 通过引入数据库层级的 `before_delete` 事件监听器，当对方执行 `/restart` 导致交易或密使被级联删除（Cascade Delete）时，系统会自动将待处理的托管资源及执行中的密使返还给发送方公园（适用容量上限限制），有效防范了资源流失（Leakage）问题。
- **Q: 当两个公园同时向对方发送外交请求（结盟/敌对）时，是否会产生重复的关系 或矛盾的状态（既是盟友又是敌人）？**
  - **A:** [v1.8.5] 通过在储存外交关系时强制执行 Canonical Ordering（`park_a_id < park_b_id`）并引入 `initiator_id` 字段，数据库的 UniqueConstraint 能高度预防重复关系的生成。此外，我们采用按 ID 排序的 2 向悲观锁以高度预防死锁，并使用批量更新（`update()`）一并解除两公园间所有 active/pending 的重复关系，确保不会出现矛盾状态或解除遗漏。
- **Q: 在 NPC 轮次同步过程中，中间提交（Commit）是否会导致锁遗失或产生 Lost Update？**
  - **A:** [v1.8.6] 我们解决了在循环外部一次性锁定所有 NPC、并在循环内部执行提交时所产生的过早释放锁的结构性缺陷。现在，我们在循环外部仅查询 NPC ID 列表，并在循环内部采用**独立隔离的事务**对每个 NPC 进行悲观锁定（`with_for_update()`）。此外，若 NPC 的某项行动失败抛出异常，系统将启动**嵌套事务（Nested Transaction / Savepoint, `begin_nested()`）**仅回滚该失败行动，从而保护整体的悲观锁并避免轮次计数回滚（防止 Stampede 发生）。密使破坏行动也套用了 2 向锁以高度预防 TOCTOU 计算误差。
- **Q: 在拒绝交易时，恶意用户是否能篡改交易 ID 以强制拒绝他人的私密交易（IDOR）？此外，已灭亡用户的交易（Zombie Trades）是否会持续显示在市场中？**
  - **A:** [v1.8.7] 我们在交易拒绝（`trade_reject`）API 的原子化 UPDATE 条件中新增了 `receiver_id == park.id` 防护条件，强制要求只有收到提议的本人才能拒绝交易，有效防范了 IDOR 权限越权漏洞。同时，为防止已灭亡用户的交易提议持续滞留在市场中（僵尸交易），我们修改了 `trade_market()` 查询，在 SQL 阶段 JOIN `Park` 模型，仅动态筛选出发送方依然生存（`is_destroyed == False`）的交易提议进行显示。
- **Q: 在慢速路径（消耗轮次与 NPC 轮次同步）执行期间，若其他异步请求扣除 AP，是否会因过期内存覆写（Lost Update）而导致 AP 复制（免费使用）？**
  - **A:** [v1.8.8] 我们已高度缓解了 AP 复制（Lost Update）缺陷。即使在慢速路径的无锁同步间隙期间，并发的快速路径请求成功扣除了 AP，慢速路径的端点也会**重新取得玩家公园的悲观锁并强制执行 `refresh` 数据刷新**，随后才进行最终的 AP 减算，从而确保了数据的高度一致性与原子性。 (audit_report_56.md [STATE-F029])
- **Q: 在 NPC 轮次进行中发生战斗时，会因 `ResourceClosedError` 等错误导致轮次同步中断 or 陷入无限循环吗？另外，行动失败时退还的 AP 会流失吗？或是密使归还后的过密处理时会因 Lost Update 造成资源消失或复制吗？**
  - **A:** [v1.8.9] 已高度缓解。NPC 战斗内部的 `commit()` 已被替换为 `flush()` 以保护嵌套的 Savepoint，并采用双重回滚异常防御。退还的 AP 在路由异常区段内会立即执行显式的 `db.session.commit()`，防止回滚流失。最后，在 `_process_spy_missions` 的过密处理前，系统会对玩家公园再次获取 `with_for_update()` 悲观锁并执行 `refresh`，高度预防并发请求对数据的覆盖（Lost Update）。
- **Q: 当 NPC 攻击玩家或其他公园时，是否会因锁定获取顺序冲突而导致死锁（Deadlock）并耗尽 DB 连接？**
  - **A:** [v1.8.9] 已高度防范死锁漏洞 `[DEADLOCK-F005]`。我们已永久移除了在 `process_npc_turn()` 开始时无条件先行获取的悲观锁（`with_for_update()`），改为仅进行单纯刷新（`refresh`），同时在上位轮次同步调度器 `_sync_npc_turns()` 中，NPC 基本轮次处理（`process_turn`）完成后立即强制执行 `db.session.commit()` 以完全释放先行锁，随后将 `process_npc_turn()` 作为独立事务启动，全方位采用了**两阶段事务边界分离结构**。因此，当 NPC 发动攻击时，两个公园的锁仅会在 `execute_battle()` 内部依据 Canonical Ordering（按 ID 升序排序）安全地同时获取。这高度预防了因相互锁等待冲突导致的死锁及数据库连接池枯竭的问题。
