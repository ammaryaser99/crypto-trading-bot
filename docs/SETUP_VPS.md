# Ubuntu VPS deployment

This project runs the official `freqtradeorg/freqtrade:stable` Docker image. The API process listens inside its container, but Docker deliberately publishes its port only on VPS `127.0.0.1`, so it is not reachable from the public internet by default.

## 1. Prepare Ubuntu

Use a supported Ubuntu LTS host with at least 1 GB RAM and a current Docker Engine plus Docker Compose plugin. Follow Docker's official Ubuntu installation guide rather than an unmaintained third-party installer: <https://docs.docker.com/engine/install/ubuntu/>.

Verify the installation:

```bash
docker --version
docker compose version
```

Optionally allow your normal user to use Docker, then sign out and in again:

```bash
sudo usermod -aG docker "$USER"
```

## 2. Clone and configure

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY.git crypto-freqtrade
cd crypto-freqtrade
cp .env.example .env
chmod +x scripts/*.sh
nano .env
```

Leave `TELEGRAM_ENABLED=false` until the token and chat ID have been set. Replace both API placeholder values with long, unique random values even though the service binds locally.

For Binance spot paper trading, public market data commonly works with blank keys. If you choose to add API credentials, use a dedicated API key with withdrawals disabled and IP restrictions where the exchange supports them. Never place the key in `config.json` or Git.

## 3. Start the dry-run bot

```bash
./scripts/start.sh
./scripts/status.sh
```

The first startup pulls the container image. Confirm the logs say `Dry run is enabled` before leaving the VPS unattended:

```bash
docker compose logs -f freqtrade
```

## 4. Safely access the dashboard

The service is bound to VPS loopback only. From your own computer, use an SSH tunnel:

```bash
ssh -L 8080:127.0.0.1:8080 YOUR_USER@YOUR_VPS_IP
```

Then open `http://127.0.0.1:8080` in your browser and authenticate with the values in `.env`.

For a public domain, put an authenticated HTTPS reverse proxy in front of the service, keep the Docker port loopback-only, restrict firewall access, and use a long random API password/JWT secret. Do not publish `8080:8080` directly.

## 5. Stop or update

```bash
./scripts/stop.sh
git pull --ff-only
docker compose pull
./scripts/start.sh
```

Stopping the container preserves the SQLite dry-run database under `user_data/`, which is intentionally ignored by Git. Back it up separately if you want to retain the experiment history.
