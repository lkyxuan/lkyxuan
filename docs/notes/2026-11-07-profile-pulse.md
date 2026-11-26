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

# 2026-11-26 换成六轨音序器
- 从三版样片（Techno 音序器 / 大教堂与集市 / 黑客与画家）里选了音序器。
- 六轨 = 六个身份：黑客、画家、集市、大教堂、设计师各是一类仓库每天的提交，Techno 是机器心跳。
- 仓库归类在 `track_of`：kiki/kiki-core/kiki-agent 是大教堂；kiki-theme-*、kiki-pet、lumia 是画家；其它 kiki-*、*-kiki 是集市；SignalStudio 和主页类是设计师；剩下都算黑客。新仓库按名字自动归类。
- 提交数用 GraphQL commitContributionsByRepository，和贡献图口径一致（只算默认分支）。state 里只存每天每轨的数字，不存仓库名。
- K 线去掉了。心跳断了：右上角变红 FLATLINE，Techno 轨变成一条红线。
