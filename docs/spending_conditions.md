## Spending Conditions

Spending conditions (not miniscript) are rules that would be enforced by Resigner. The rules/policies are composable, flexible and are defined in the TOML format (in the [configuration file](config.md)).

- [x] Spending limits in satoshis  (per day/week/month).
- [] Presence of additional 2FA in the PSBT.
- [] Require all cosigners
- [] Whitelist addresses controlled by Resigner.

There is the concept of roles; for example: different rules can be applied to depending on the presence of some valid signature

### SpendLimit
Spending limit in satoshis; `monthly_limit >= weekly_limit >= daily_limit`.

```
[spending_limt]
daily_limit = 0  # 0.1 btc
weekly_limit = 0
monthly_limit = 0
```
