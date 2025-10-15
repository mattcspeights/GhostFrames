import { app, BrowserWindow } from "electron";
import path from "node:path";
import { spawn } from "node:child_process";
import net from "node:net";
import started from "electron-squirrel-startup";

if (started) app.quit();

let backendProc = null;

async function waitForPort(port, timeoutMs = 8000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    (function probe() {
      const s = net.connect(port, "127.0.0.1", () => {
        s.end();
        resolve();
      });
      s.on("error", () => {
        s.destroy();
        if (Date.now() - start > timeoutMs) reject(new Error("backend timeout"));
        else setTimeout(probe, 150);
      });
    })();
  });
}

async function startBackend() {
  const isDev = !app.isPackaged;
  const devPy = path.join(process.cwd(), "backend", "api.py");
  const prodBin = path.join(
    process.resourcesPath,
    process.platform === "win32" ? "backend.exe" : "backend"
  );

  const cmd = isDev ? "python" : prodBin;
  const args = isDev ? [devPy, "--print-port"] : ["--print-port"];

  backendProc = spawn(cmd, args, { stdio: ["ignore", "pipe", "pipe"], windowsHide: true });

  // Read the single line of JSON printed by the backend
  const port = await new Promise((resolve, reject) => {
    backendProc.stdout.once("data", (buf) => {
      try {
        const data = JSON.parse(buf.toString());
        resolve(data.port);
      } catch (e) {
        reject(e);
      }
    });
  });

  await waitForPort(port);
  return `http://127.0.0.1:${port}`;
}

async function createWindow() {
  const baseURL = await startBackend();

  const mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    icon: "lockheed.png",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
    },
  });

  // When developing, still use Vite dev server URL
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL);
  } else {
    // For production builds, you can either load your bundled UI
    // or point directly to the backend (if it's serving HTML)
    mainWindow.loadFile(
      path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`)
    );
  }

  // Example: if your frontend talks to backend REST API, pass the URL
  mainWindow.webContents.executeJavaScript(
    `window.BACKEND_URL = '${baseURL}'`
  );
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (backendProc) backendProc.kill();
});
