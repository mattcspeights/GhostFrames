import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'node:path';
import { spawn } from 'node:child_process';
import started from 'electron-squirrel-startup';

if (started) {
  app.quit();
}

let backendProcess;

const createWindow = () => {
  const mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    icon: "lockheed.png",
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
    },
  });
  startBackend();
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`));
  }

  
};

function startBackend() {
  // Point to your backend executable location.
  // For production builds, use `process.resourcesPath` because Electron packs files differently.
  const backendPath = path.join(
    process.env.NODE_ENV === 'development'
      ? path.resolve('./dist/api.exe')
      : path.join(process.resourcesPath, 'api', 'api.exe')
  );

  backendProcess = spawn(backendPath, [], {
    stdio: 'inherit', // You can use 'pipe' to capture logs if needed
  });

  backendProcess.on('error', (err) => {
    console.error('Failed to start backend:', err);
  });

  backendProcess.on('close', (code) => {
    console.log(`Backend exited with code ${code}`);
  });
}

// Stop backend when Electron quits
app.on('before-quit', () => {
  if (backendProcess) backendProcess.kill();
});

app.whenReady().then(() => {
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
