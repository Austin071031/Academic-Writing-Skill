# 提交记录（playground submission）

| 项目 | 内容 |
|-|-|
| **Playground Attempt ID** | **88991** |
| 挑战赛 | challenge-308a6fdc（写作01｜学术论文写作） |
| 提交时间 | 2026-11-19T04:00:07+00:00 |
| 状态 | pending_review（待人工评审） |
| 得分 | 暂无最终分（score=0 为占位，`score_is_final=false`；评分卡 `non_scored_subtype=evaluation_error`） |
| 模型 / Harness | SciMaster / SciMaster |
| Bundle | 335,090 bytes，sha256 `e6f8a966bba820f098743c95cf39d7c709a99647c1c82457ee7dd44b7b887fbd` |
| 查询命令 | `playground status --attempt-id 88991` |
| GitHub 公开链接（附加分用） | https://github.com/Austin071031/Academic-Paper-Writing-Skill |

## 执行状态说明（如实记录）

本次提交在评测端复跑时返回 `harbor_status=evaluation_error`（`playground-worker/harbor-lbg`，
`harbor_replay_executed=1`），即 Harbor 复跑阶段报错，未产生可评分结果；记录状态仍为
`pending_review`，故保留等待人工评审或后续重提。同一账号同期另有一次提交（89028，
学术格式与模板适配）出现同类 `evaluation_error`，且本地端到端自测（合成案例）通过，
初步判断为评测端复跑异常而非 Skill 运行失败；该判断未经平台确认，不作为结论。

若需重提：本目录内容即提交包内容，重提后请在此追加新的 Attempt ID 行，保留本次记录不覆盖。

## 版本与提交的对应关系

本目录（v1.0.0）的全部文件与 attempt 88991 打包上传的 skill 内容对应。
每个版本一次 playground 提交，Attempt ID、得分在本文件回填，
形成"版本—提交—得分"可追溯链。映射规则：同一挑战赛下按提交时间顺序对应版本号顺序。
