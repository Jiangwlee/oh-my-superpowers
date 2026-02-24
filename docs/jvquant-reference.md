# JVQuant 平台参考文档

> 官方文档: https://jvquant.com/wiki/
> 最后更新: 2026-02-24

## 一、平台概述

JVQuant 是一个金融数据 OpenAPI 平台，提供三大核心服务：

1. **实时行情** — WebSocket 推送（沪深/港股/美股）
2. **数据库服务** — HTTP 查询（K线/分时/Level2/基本信息/语义查询）
3. **券商交易接口** — HTTP 柜台直连（查询持仓/委托/买卖/撤单）

本项目（a-share-review-planner）**仅使用券商交易接口**获取个人账户数据（持仓、委托、资金），行情和数据库服务由 akshare/爬虫免费获取。

---

## 二、接入流程

### 2.1 注册与认证

1. 注册账户: http://jvquant.com/register.html
2. 注册后获得唯一 **Token**（JVQUANT_APP_TOKEN）
3. Token 是所有 API 调用的身份凭证，泄露后可通过绑定邮箱重置

### 2.2 分配柜台服务器

每次使用前需动态分配业务服务器（地址可能变化）：

```
GET http://jvquant.com/query/server?market=ab&type=trade&token=<Token>

返回:
{"code": "0", "server": "<柜台地址>"}
```

参数说明：
| 参数 | 值 | 说明 |
|------|------|------|
| market | `ab` / `hk` / `us` | 沪深 / 港股 / 美股 |
| type | `trade` / `websocket` / `sql` | 交易 / 行情 / 数据库 |

### 2.3 登录柜台获取 Ticket

```
GET http://<柜台地址>/login?token=<token>&acc=<资金账号>&pass=<密码>

返回:
{"code": "0", "ticket": "<登录凭证>", "expire": "<有效时间(秒)>"}
```

**重要**: 每次 login 调用会产生计费（5毛/次）。必须缓存 ticket，在 expire 内复用。

---

## 三、交易接口 API

### 3.1 查询持仓（check_hold）

```
GET http://<柜台地址>/check_hold?token=<token>&ticket=<ticket>
```

返回字段：
| 字段 | 说明 |
|------|------|
| total | 账户总资产 |
| usable | 可用资金 |
| day_earn | 当日盈亏 |
| hold_earn | 持仓盈亏 |
| hold_list[].code | 证券代码 |
| hold_list[].name | 证券名称 |
| hold_list[].hold_vol | 持仓数量 |
| hold_list[].usable_vol | 可用数量 |
| hold_list[].day_earn | 当日盈亏 |
| hold_list[].hold_earn | 持仓盈亏 |

### 3.2 查询委托（check_order）

```
GET http://<柜台地址>/check_order?token=<token>&ticket=<ticket>
```

返回字段（list 数组）：
| 字段 | 说明 |
|------|------|
| order_id | 委托编号 |
| day | 委托日期 (YYYYMMDD) |
| time | 委托时间 (HHMMSS) |
| code | 证券代码 |
| name | 证券名称 |
| type | 委托类型（证券买入/证券卖出） |
| status | 委托状态（已成/已报/已撤等） |
| order_price | 委托价格 |
| order_volume | 委托数量 |
| deal_price | 成交价格 |
| deal_volume | 成交数量 |

### 3.3 交易委托（buy/sale）

```
GET http://<柜台地址>/buy?token=<token>&ticket=<ticket>&code=<代码>&name=<名称>&price=<价格>&volume=<数量>
GET http://<柜台地址>/sale?token=<token>&ticket=<ticket>&code=<代码>&name=<名称>&price=<价格>&volume=<数量>

返回:
{"code": "0", "message": "", "order_id": "<委托编号>"}
```

### 3.4 撤销委托（cancel）

```
GET http://<柜台地址>/cancel?token=<token>&ticket=<ticket>&order_id=<委托编号>

返回:
{"code": "0", "message": "<撤单结果>"}
```

---

## 四、计费标准

### 4.1 券商交易接口（本项目使用）

| 操作 | 单价 | 说明 |
|------|------|------|
| 柜台连接 (login) | **5毛/次** | 必须缓存 ticket 复用 |
| 查询持仓 | 2分/次 | |
| 查询交易 | 2分/次 | |
| 委托买入 | 2毛/次 | |
| 委托卖出 | 2毛/次 | |
| 撤销委托 | 2毛/次 | |

### 4.2 数据库服务（本项目不使用）

每日免费查询次数 = 账户积分 * 1%，超出后 1分/次。

| 数据类别 | 单价/次 |
|---------|---------|
| K线查询 | 1分 |
| 分时行情 | 1分 |
| 逐笔委托队列 | 1分 |
| 千档盘口队列 | 1分 |
| 股票基本信息 | 1分 |
| 可转债信息 | 1分 |
| 自定义查询 | 1分 |
| 历史分时数据包 | **20元** |

### 4.3 实时行情（本项目不使用）

每日免费订阅 = 账户积分 * 0.5%，超出后：

| 行情类别 | 单价 |
|---------|------|
| 沪深基础行情 | 2分/支/天 |
| 沪深十档行情 | 1毛/支/天 |
| 沪深L2逐笔成交 | 2毛/支/天 |
| 港股基础 | 6分 |
| 美股基础 | 8分 |

---

## 五、费用优化策略

### 5.1 核心原则：JVQuant 仅用于不可替代的数据

| 数据需求 | 推荐来源 | 原因 |
|---------|---------|------|
| 个人持仓 | **JVQuant** (唯一) | 只有券商柜台能获取真实持仓 |
| 个人委托记录 | **JVQuant** (唯一) | 只有券商柜台能获取真实委托 |
| 账户资金 | **JVQuant** (唯一) | 只有券商柜台能获取真实资金 |
| 个股K线 | akshare / 金融界 | 免费 |
| 北向资金 | akshare | 免费 |
| 资金流向 | 金融界 / 东方财富 | 免费 |
| 板块行情 | 同花顺 / 东方财富 | 免费 |
| 实时行情 | 东方财富 / 金融界 | 免费（延迟行情） |
| 新闻资讯 | 金融界 | 免费 |
| 社区舆情 | 淘股吧 / 东方财富股吧 | 免费 |

### 5.2 Ticket 缓存机制（已实现）

当前 `broker_account.py` 已实现 ticket 缓存：
- 缓存路径: `~/.openclaw/.jvquant_ticket_cache.json`
- 在 expire 时间内复用 ticket，避免重复 login 计费
- 预留 60 秒 buffer 防止边界过期

### 5.3 费用估算（每日复盘场景）

| 操作 | 次数 | 单价 | 费用 |
|------|------|------|------|
| login | 1 | 5毛 | 0.5元 |
| check_hold | 1 | 2分 | 0.02元 |
| check_order | 1 | 2分 | 0.02元 |
| **日均合计** | | | **~0.54元** |
| **月均合计** | ~22天 | | **~11.88元** |

> 如果 ticket 缓存有效（同日多次调用），login 不会重复计费，实际费用更低。

---

## 六、环境变量配置

本项目涉及的环境变量：

```bash
# JVQuant 平台认证（必需）
JVQUANT_APP_TOKEN=<jvquant平台token>

# 东方财富交易账户（通过 JVQuant 柜台登录）
EASTMONEY_ACCOUNT=<资金账号>
EASTMONEY_PASSWORD=<资金密码>
```

### 映射关系

当前 `broker_account.py` 使用的环境变量名与上述不同，需要适配：

| 用户环境变量 | broker_account.py 当前变量名 | 说明 |
|-------------|---------------------------|------|
| JVQUANT_APP_TOKEN | JVQUANT_TOKEN | jvQuant 平台 token |
| EASTMONEY_ACCOUNT | JVQUANT_ACC | 东方财富资金账号 |
| EASTMONEY_PASSWORD | JVQUANT_PASS | 东方财富资金密码 |
| (无，动态获取) | JVQUANT_COUNTER | 柜台地址（应改为动态分配） |

### 改进方向

1. **柜台地址动态分配**: 当前需要手动配置 `JVQUANT_COUNTER`，应改为通过 `/query/server` 接口自动获取
2. **环境变量名统一**: 将内部变量名映射到用户提供的 `JVQUANT_APP_TOKEN` / `EASTMONEY_ACCOUNT` / `EASTMONEY_PASSWORD`
3. **柜台地址缓存**: 分配的柜台地址可能变化，但短期内可缓存复用，避免每次都请求

---

## 七、券商限制

- **普通账户仅支持东方财富**（机构账户无限制）
- 东方财富开户链接: https://zqhd.18.cn/shouji.html?from=GDTS-5482-JDNS
- 支持品类: 股票、可转债、ETF基金

---

## 八、注意事项

1. **Token 安全**: Token 是 API 凭证，禁止硬编码或提交到版本库
2. **计费感知**: login 最贵（5毛），查询便宜（2分），交易中等（2毛）
3. **服务器变化**: 每次连接前应重新查询柜台地址（或设置合理缓存时间）
4. **账单周期**: 交易账单 1 分钟聚合，行情账单 5 秒聚合
5. **隐私保护**: jvQuant 不记录调用明细，仅提供聚合统计
