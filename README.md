# MT5 Firm Dusty Dragon

Dusty Dragon is a paper-first digital trading-firm research platform inspired by HKUDS/Vibe-Trading, Conway-Research/automaton, and shiyu-coder/Kronos.

## Data storage policy

GitHub stores source code, schemas, tests, and small configuration examples only. Large historical market datasets, backtest inputs, generated research datasets, and archive chunks must not be committed.

Dusty Dragon stages historical data as compressed, checksummed partitions by broker / symbol / timeframe / year / month and can archive those chunks to Google Drive. The intended Drive account is `forex.isekai@gmail.com`; runtime OAuth verifies the connected account before upload.

Google OAuth client secrets and refresh tokens remain local runtime secrets and are excluded by `.gitignore`. The ChatGPT Google Drive connection is not reused by the running bot; Dusty Dragon must authorize its own Google Drive access on the machine or VPS where it runs.
