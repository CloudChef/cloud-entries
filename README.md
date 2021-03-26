# CloudEntries
该项目旨在为 SmartCMP 产品提供一种通用的云平台扩展方法，支持用户自定义新的云平台类型，并且能够自定义资源类型、查询接口、生命周期管理脚本。

## 代码结构说明
```text
└── cloudentries
    ├── <cloud_type>                  # 定义云平台类型
    │   ├── lifecycles                # 该目录用于定义生命周期管理脚本，目前支持Python3脚本
    │   │   ├── __init__.py           # 在该文件中定义 cloudentry_id，如："yacmp:cloudentry:type:generic-cloud:fusionaccess"
    │   └── query                     # 该目录用于定义资源类型和资源查询脚本，目前支持Python3脚本
    │   │   ├── __init__.py           # 在该文件中注册云平台资源类，如：Platforms(cloudentry_id, FusionAccessResource)
    │   │   ├── cloud.yaml            # 在该文件中定义云平台类型、支持的资源类型、以及对接该云平台所需要的参数
    │   │   ├── resource_config.json  # 在该文件中定义各个云资源申请时所需要填写参数
```

## 编译
该项目的代码会以插件的形式集成到 SmartCMP 产品中。

## 如何贡献代码
我们随时都欢迎任何贡献，无论是简单的错别字修正，BUG 修复还是增加新功能。请踊跃提出问题或发起 PR。我们同样重视文档以及与其它开源项目的整合，欢迎在这方面做出贡献。
参照下面的 GitHub 工作流指引解决 issue 并按照规范提交 PR，通过 review 后就会被 merge 到 master(main) 分支。

### Github PR 提交工作流
1. 将仓库 fork 到自己的 GitHub 下
2. 将 fork 后的仓库 clone 到本地
3. 创建新的分支，在新的分支上进行开发操作（请确保对应的变更都有测试用例或 demo 进行验证）
4. 保持分支与远程 master(main) 分支一致（通过 fetch 和 rebase 操作）
5. 在本地提交变更（注意 commit log 保持简练、规范），注意提交的 email 需要和 GitHub 的 email 保持一致
6. 将提交 push 到 fork 的仓库下
7. 创建一个 pull request (PR)
8. 提交 PR 的时候请参考 PR 模板

### PR 模板
- 描述这个PR做了什么或者为什么我们需要这个PR
- 这个PR修复了某个关联的 Issue
- 描述这个PR的代码逻辑
- 描述如何验证该PR
- 一些给Reviewer的comments

## 如何提交 Issue
如何您有任何使用建议、Bug Reports或者任何疑惑都可以提交到 https://github.com/CloudChef/cloud-entries/issues

## 在线体验
[SmartCMP SaaS](https://console.smartcmp.cloud/#/main/welcome)

## License
Apache License 2.0, 参考 [LICENSE](LICENSE).
