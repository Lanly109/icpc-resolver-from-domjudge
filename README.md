# icpc-resolver-from-domjudge

A tools to generate xml file of icpc-resolver via domjudge RESTful API.

一键生成带有奖项信息的滚榜数据，适用于`resolver`。

默认生成奖项：
- 全场第一名（World Champion）
- 正式队伍前三名
- 金牌队伍
- 银牌队伍
- 铜牌队伍
- 最佳女队奖
- 正式队伍的一血奖
- 顽强拼搏奖
- ~~第一发WA奖~~

其中打星队伍会颁发金银铜，但不会占用总获奖名额。

在生成`json`的同时还会生成对应名字的`csv`，包含队伍的信息和奖项，方便制作获奖队伍PPT。

`resolver`源码阅读记录：[滚榜程序Resolver源码阅读](https://lanly109.github.io/posts/7b2538bb.html)

## Prerequisite

推荐 [icpc-resolver 2.5.940](https://github.com/icpctools/icpctools/releases/download/v2.5.940/resolver-2.5.940.zip) 或 [icpc-resolver 2.5.1160](https://github.com/icpctools/icpctools/releases/download/v2.6.1160/resolver-2.6.1160.zip)

## Usage
1. setup config.json
### config.json
```jsonld
{
  "url": <contest api url>,
  "username": <username whose role is api_reader>,
  "password": <password of the user>,
  "xml": <output xml file name>,
  "json": <output xml file name>,,
  "gold": <the number of gold medals>,
  "silver": <the number of silver medals>,
  "bronze": <the number of bronze medals>,
  "gold_show_list": true/false,
  "silver_show_list": true/false,
  "bronze_show_list": true/false,
  "honors_show_list": true/false,
  "no_occupy_award_categories": [<group_id1>, <group_id2>, ...],
  "award_best_girl": [<group_id1>]
}
```

- 登录的`user`需为`api_reader`角色。

- `no_occupy_award_categories`表示给位于牌区的打星队也能够展示图片（赋予`Star Team`的奖项）。

- 打星选手不参与一血奖。

#### example
```jsonld
  "url": "https://www.example.com/api/v4/contests/{cid},
  "username": "cds",
  "password": "cds",
  "xml": "events.xml"
  "json": "event-feed",
  "gold": 16,
  "silver": 32,
  "bronze": 47,
  "gold_show_list": false,
  "silver_show_list": true,
  "bronze_show_list": true,
  "honors_show_list": true,
  "no_occupy_award_categories": ["18", "20"],
  "award_best_girl": ["11"]
```
2. run main.py
```
python3 main.py
```

将生成的`event-feed.json`文件放入[CDP](https://clics.ecs.baylor.edu/index.php/CDP)格式的目录下，运行`Resolver`。

```bash
./resolver.sh /path/to/cdp
``` 

#### tip

Resolver 2.5版的`CDP`目录格式如下：

```bash
.
├── contest
│   └── logo.png        // resolver主页面的图片&无照片队伍的默认照片
├── event-feed.json     // 上述python工具生成的json
├── organizations       // Affiliations照片，只要某Affiliations的队伍有logo，其他同Affiliations的队伍就都是该logo
│   ├── 2              // Affiliations的id
│   │   └── logo.png
└── teams               // 队伍照片
    ├── 3000            // 队伍的id
    │   └── photo.png   
    ├── 3001
    │   └── photo.png
    ├── 3009
    │   └── photo.png
    └── 3010
        └── photo.png
``` 

## 更新log

### 2025.05.11

适配`PTA`版本

### 2025.04.18

更新适应domjudge >= 8.2。`PTA`版本未测试！

7.0的请参考`domjudge7`分支。

提供一个`CDP`格式的`demo`文件夹，`resolver`的运行指令：
```bash
./resolver.sh ./demo
```

### 2023.05.14

新增适用于`PTA`平台的，`CCPC Final`评奖规则的类`PTA_School`。奖项用中文+`Emoji`表情，字体用的是`Noto Sans CJK`.
评奖规则：
1. 按学校排名颁奖金银铜
2. 本科组与专科组分开颁奖
3. 非校内第一队伍按后续队伍的校排作为排名。

`pta.json`说明：
```jsonld
{
  "url": "https://pintia.cn/api/xcpc/problem-sets/<PID>/",
  "file":"",
  "username": <pta email>,
  "password": <pta password>,
  "xml": "events",
  "ben": {
      "group": [1],
      "gold": 10,
      "silver": 20,
      "bronze": 30,
      "first": 3,
      "suffix": ""
  },
  "zhuan": {
      "group": [2],
      "gold": 1,
      "silver": 2,
      "bronze": 3,
      "first": 3,
      "suffix": "(专科)"
  }
}
```

- `file`指本地的`eventfeed`，若不为空则从本地文件读取，否则通过`url`获取。
- `ben`即本科组奖项设置，`zhuan`即专科组奖项设置，`group`表示参与评奖的组别，然后是金银铜，以及冠亚季（前3），`suffix`表示奖项的后缀。（感觉应该放到一个`medal`列表更好）

### 2022.10.06

不用再获取`Basic Authorization key`，改为用账号登录的方式
