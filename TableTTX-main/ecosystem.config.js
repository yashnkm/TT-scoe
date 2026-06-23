// PM2 process manager config for TableTTX (Flask + OR-Tools).
//
// PM2 runs gunicorn (NOT the Flask dev server). On the AWS free-tier box this
// keeps the app alive across crashes/reboots with simple start/stop commands:
//
//   pm2 start ecosystem.config.js     # start
//   pm2 stop tabletx                  # stop
//   pm2 restart tabletx               # restart
//   pm2 logs tabletx                  # tail logs
//   pm2 save && pm2 startup           # survive EC2 reboot
//
// Edit env values below (or set them in a .env file, which app.py loads too).

module.exports = {
  apps: [
    {
      name: "tabletx",
      // Use the venv's gunicorn so the right Python/deps are picked up.
      script: "./venv/bin/gunicorn",
      // app:app  ->  module app.py, Flask object named `app`
      args: "--workers 1 --threads 2 --timeout 180 --bind 0.0.0.0:5001 app:app",
      cwd: __dirname,
      interpreter: "none", // script is a binary, not a JS file
      autorestart: true,
      max_restarts: 10,
      // 1 GB free-tier box: restart if the process bloats past ~700 MB.
      max_memory_restart: "700M",
      env: {
        // --- REQUIRED in production ---
        SESSION_SECRET: "CHANGE_ME_to_a_long_random_string",
        OPENAI_API_KEY: "sk-...",          // your OpenAI key (AI assistant)
        // --- Tuned for 1 vCPU / 1 GB free tier (see solver.py) ---
        SOLVER_WORKERS: "1",               // was 4; 1 vCPU box -> 1
        SOLVER_TIMEOUT: "120"
      }
    }
  ]
};
