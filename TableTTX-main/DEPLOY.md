# Deploying TableTTX on AWS Free Tier (EC2 + PM2)

Simple setup: one EC2 free-tier VM, app exposed directly on its public IP,
started/stopped with PM2. No nginx, no domain.

## 1. Launch the EC2 instance

- **AMI:** Ubuntu Server 22.04 LTS (free-tier eligible)
- **Type:** `t3.micro` or `t2.micro` (free tier — 1 vCPU, 1 GB RAM)
- **Key pair:** create/download one so you can SSH in
- **Security group (firewall) — inbound rules:**
  - SSH (TCP 22) from *My IP*
  - Custom TCP **5001** from `0.0.0.0/0`  ← this is how you reach the app

> 1 GB RAM is tight for OR-Tools. If the solver gets OOM-killed, add a 2 GB swap file:
> ```bash
> sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
> sudo mkswap /swapfile && sudo swapon /swapfile
> echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
> ```

## 2. SSH in and install system deps

```bash
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>

sudo apt update
sudo apt install -y python3-venv python3-pip git nodejs npm
sudo npm install -g pm2          # PM2 process manager
```

## 3. Get the code

```bash
git clone https://github.com/yashnkm/TT-scoe.git
cd TT-scoe
git checkout dev_2               # current branch with latest commit
```

## 4. Python venv + dependencies

```bash
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

## 5. Configure secrets

Edit `ecosystem.config.js` and set:
- `SESSION_SECRET` → a long random string (`openssl rand -hex 32`)
- `OPENAI_API_KEY` → your OpenAI key (needed for the AI assistant)

`SOLVER_WORKERS=1` is already set for the 1-vCPU box — leave it.

## 6. Start with PM2

```bash
pm2 start ecosystem.config.js
pm2 save           # remember the process list
pm2 startup        # run the printed command so it survives reboots
```

App is now live at: **http://<EC2_PUBLIC_IP>:5001**

## Everyday commands

| Action            | Command                  |
|-------------------|--------------------------|
| Stop              | `pm2 stop tabletx`       |
| Start             | `pm2 start tabletx`      |
| Restart           | `pm2 restart tabletx`    |
| Logs (live)       | `pm2 logs tabletx`       |
| Status            | `pm2 status`             |

## Updating after a git push

```bash
cd ~/TT-scoe
git pull
./venv/bin/pip install -r requirements.txt   # only if deps changed
pm2 restart tabletx
```

## Notes / gotchas

- **Data is just JSON files in `data/`.** They live on the instance's disk and
  persist across restarts/reboots, but are **lost if the instance is terminated**.
  Back them up: `tar czf data-backup.tgz data/`.
- The Flask **dev server (`app.py` `debug=True`) is NOT used** in this setup —
  gunicorn imports `app:app` directly, so debug mode never runs. Good.
- Free tier is time-limited (12 months) and metered; stop the instance when idle
  to conserve hours.
