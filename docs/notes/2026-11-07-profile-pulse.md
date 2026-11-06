# 主页心跳 + commit K 线
- 目标：替换贪吃蛇，让人第一眼记住，而不是追流行。
- 调研结论：自己写。看过 Platane/snk、github-profile-3d-contrib、lowlighter/metrics、github-readme-stats、Readme Atelier、termfetch，都是数据展示或模板，和“第一眼记住”不是一回事。
- 关键决定：
  - 标题不用 “Your data never leaves”，因为 Kiki 可以调云端模型，这句话说得太满。
  - 不写地点和本地时区，时间统一 UTC，避免公开位置。
  - 心跳是真实上报：Kiki 进程在跑才算一次，没有补数据。
  - K 线的价格是滚动 7 天提交数，每根蜡烛跨 7 天。
  - 机器死了自己报不了，所以由云端 Action 负责把图变红。
- 后续：GitHub 定时任务在仓库长期不活跃时可能被停用，上线后留意。
