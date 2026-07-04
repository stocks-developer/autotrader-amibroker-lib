# AutoTrader Web AmiBroker Library: Multi-Account Automated Trading (AFL) for 40+ Indian Brokers

> Place orders from your **AmiBroker** strategy into one account or many at once, across **40+ Indian brokers**. A ready-made AFL library with sample strategies for regular, bracket and cover orders, scanners, button trading and multi-account trading. Part of **[AutoTrader Web](https://stocksdeveloper.in/)** by **Stocks Developer**.

[![Brokers supported](https://img.shields.io/badge/brokers-40%2B-2ea44f)](https://stocksdeveloper.in/#supported-brokers)
[![Free trial](https://img.shields.io/badge/free%20trial-1%20month-blue)](https://webx.stocksdeveloper.in/register)
[![Uptime](https://img.shields.io/badge/uptime-99.98%25-brightgreen)](https://stocksdeveloper.in/features/)
[![Setup guide](https://img.shields.io/badge/docs-AmiBroker%20setup-8a2be2)](https://stocksdeveloper.in/documentation/client-setup/amibroker-library/)

---

## What is this library?

The **AutoTrader Web AmiBroker library** is an AFL library that lets you place orders from your AmiBroker strategy into single or multiple broker accounts. It ships ready-made sample AFLs for regular, bracket and cover orders, scanners, button trading and multi-account trading.

- **Broker independent.** The same strategy trades on any broker AutoTrader Web supports, across 40+ Indian brokers. No broker-specific code.
- **Single or multi-account.** Send an order to one account or many at once.
- **Ready-made samples.** Regular / bracket / cover orders, scanners, button trading and multi-account templates included.
- **Bridge connection.** Your AFL writes order requests locally, and the AutoTrader Desktop Client sends the real instructions on to your broker.

## What is AutoTrader Web?

**[AutoTrader Web](https://stocksdeveloper.in/)** by **Stocks Developer** is copy trading and multi-account software for Indian brokers. Monitor every broker account on one screen and act across all of them at once.

- **All your accounts, one screen.** Live, consolidated P&L, holdings, positions, orders and margins across every account and broker.
- **Copy trading, two ways.** PMS copy from our terminal, and master-child copy in the background, across brokers, with per-account sizing. [Copy trading software](https://stocksdeveloper.in/copy-trading-software/)
- **Bulk orders.** Place, modify, cancel and square-off across many accounts in one action.
- **GTT, bracket and cover orders**, order slicing and market price protection.
- **TradingView automation.** Turn your own chart alerts into real orders.
- **APIs and SDKs.** AmiBroker, MetaTrader and Excel, plus Java, Python, C# and HTTP REST / CSV.
- **8+ years in operation. 99.98% uptime. 40+ brokers. Under 100 ms data latency.**

## Why traders and developers choose us

- 🆓 **Free static IP included** with every account. Saves up to **₹500 per broker account per month** that other tools charge extra for.
- 💸 **One of the lowest prices in the category.** **₹295 to ₹495 per account per month**, all taxes and the static IP included. No setup fee, no hidden charges.
- ☁️ **Nothing to install for the platform.** Monitor and trade from your browser on PC or mobile, from anywhere.
- 🔗 **40+ Indian brokers on one platform.** One of the widest broker coverages available.
- 🔁 **Two ways to copy trade**, PMS and master-child, both included.
- 🔒 **Security you control.** API credentials encrypted and stored in India, broker OAuth login and two-factor authentication, portfolio data never stored, plus a Kill Switch and a full activity log.
- 🎁 **Free 1-month trial** on supported brokers.

## Supported brokers

AutoTrader Web works with **40+ Indian brokers**:

5paisa · AC Agarwal · Aetram Trades · Alice Blue · Ambalal Shares · Anand Rathi · Angel One · Arham Share · ATS · AxisDirect · Choice · DBOnline · Dhan · Eureka Share · Finvasia · Flattrade · FYERS · Groww · IIFL Securities · Jainam (Prop & Retail) · Kotak Securities · Mastertrust · Mirae Asset Sharekhan · MLB Stock Broking · Motilal Oswal · Nuvama · PL Capital (PLIndia) · Profitmart · Pune E-Stock Broking (PESB) · Raghunandan Money · Religare · Share India (Prop & Retail) · SMC India · Stocko · SW Capital · Tradejini · Tradeswift · Upstox · Wisdom Capital · Zebu · Zerodha

*Plus any broker that supports the Symphony XTS API.* See the [full, always-current broker list](https://stocksdeveloper.in/#supported-brokers) and the [broker setup guides](https://stocksdeveloper.in/documentation/supported-brokers/).

## Quick start

AmiBroker is a **bridge** client, so it works together with the AutoTrader Desktop Client running on your computer.

1. Install and start the [AutoTrader Desktop Client](https://stocksdeveloper.in/documentation/client-setup/desktop-client/).
2. On its **Settings** tab, click **Amibroker Library Install** and select your AmiBroker folder. This copies the AFL library into AmiBroker's `Formulas\Include` folder.
3. Include the library at the top of your strategy AFL:

```c
#include <autotrader.afl>
```

4. Place an order. The same call works on every supported broker:

```c
orderId = placeOrder(AT_ACCOUNT, AT_EXCHANGE, AT_SYMBOL,
    "BUY", "MARKET", AT_PRODUCT_TYPE, AT_QUANTITY,
    buyPrice, defaultTriggerPrice(), True);
```

Ready-made sample AFLs (regular / bracket / cover orders, scanners, button trading and multi-account trading) install under `Formulas\AutoTraderWeb`.

Full step-by-step guide: **[AmiBroker library setup](https://stocksdeveloper.in/documentation/client-setup/amibroker-library/)**. See also [multi-account button trading](https://stocksdeveloper.in/amibroker-multi-account-button-trading/). Get your API key from your [account settings](https://webx.stocksdeveloper.in/register).

## Open-source AmiBroker utilities

This repository also includes free, open-source AmiBroker AFL utilities under [`Formulas/`](Formulas/). They provide ready-made helper functions for common tasks that are not built into AmiBroker, to make writing AFL strategies easier. Use them as a reference and copy the code into your own AFL files.

## Pricing and free trial

- **Free 1-month trial** on supported brokers, with every feature included.
- Then **₹295 to ₹495 per account per month**. All taxes and a free static IP are included. No setup fee, no hidden charges.
- [See full pricing](https://stocksdeveloper.in/pricing/) · [Start free](https://webx.stocksdeveloper.in/register)

## Documentation and links

| Resource | Link |
|---|---|
| 🌐 Website | https://stocksdeveloper.in/ |
| ✨ Features | https://stocksdeveloper.in/features/ |
| 💰 Pricing | https://stocksdeveloper.in/pricing/ |
| 🔁 Copy trading software | https://stocksdeveloper.in/copy-trading-software/ |
| 🏦 Supported brokers | https://stocksdeveloper.in/#supported-brokers |
| 🔒 Security and data handling | https://stocksdeveloper.in/security/ |
| 📘 Documentation | https://stocksdeveloper.in/documentation/getting-started/ |
| 🧩 API reference | https://stocksdeveloper.in/documentation/api/ |
| ⚙️ AmiBroker library setup | https://stocksdeveloper.in/documentation/client-setup/amibroker-library/ |
| 🖥️ Desktop Client setup | https://stocksdeveloper.in/documentation/client-setup/desktop-client/ |
| 🆓 Start free (1-month trial) | https://webx.stocksdeveloper.in/register |
| ✉️ Contact us | https://stocksdeveloper.in/contact/ |

## About Stocks Developer

Stocks Developer is a technology company building software tools for Indian markets, shaped by 8+ years of trader feedback. Our software runs on Google Cloud in its Mumbai, India region for fast, low-latency performance, with strong security and high reliability.

Stocks Developer provides software tools only. It gives no investment advice, tips, recommendations, or trading strategies, and it makes no trading decisions for you. All trading and investment decisions remain solely your responsibility. You set up and control every activity, and you can stop it at any time.

## License

See [LICENSE](LICENSE).
