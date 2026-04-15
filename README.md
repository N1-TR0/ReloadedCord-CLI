# ReloadedCord CLI

<p align="center">
  <img src="https://i.imgur.com/3lcHYNZ.png" width="500">
</p>

<p align="center">
  <strong>A lightweight TUI-based Discord patcher for legacy macOS</strong>
</p>

---

## 🚀 Features

* **Auto-Detection:** Automatically identifies your macOS version and hardware model.
* **Native macOS Integration:** Spawns a native AppleScript "Save As" window to choose your output location.
* **Smart Version Picker:** Pre-selects the optimal Discord build for your specific OS (10.9 through 10.15).
* **Visual Progress:** Real-time logging and progress bars within a clean, purple-themed Terminal UI.

---

## 🖼️ Preview

<p align="center">
  <img src="https://i.imgur.com/hLiXr6n.png" width="700">
</p>

---

## 📋 Prerequisites

Before running the script, ensure you have the following installed:

1.  **Python 3.6+**
2.  **Node.js & npm** (Required for `asar` processing)
3.  **Asar:** Install globally via terminal:
    ```bash
    npm install -g @electron/asar
    ```
4.  **Requests:** Install the Python dependency:
    ```bash
    pip3 install requests
    ```

---

## 🛠️ Installation & Usage

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/N1-TR0/ReloadedCord.git
    cd ReloadedCord
    ```

2.  **Run the script:**
    ```bash
    python3 main.py
    ```

3.  **Follow the TUI Prompts:**
    * **Select Version:** Use the arrow keys to confirm the macOS version you are targeting.
    * **Save Path:** A macOS dialog will appear. Choose where you want to save the `DiscordPatched.dmg`.
    * **Confirm:** Press `Y` to begin the patching process.

---

## 🖥️ Technical Details

The script performs the following steps automatically:

1.  **Fetch:** Downloads the specific `.dmg` from Discord's official servers.
2.  **Mount:** Uses `hdiutil` to mount the image and extract the `.app` bundle.
3.  **Unpack:** Uses `npx asar` to unpack the core application resources.
4.  **Patch:** Replaces the update logic to ignore host-level version mismatches.
5.  **Repack:** Re-bundles the app and converts it into a compressed, read-only UDZO DMG.

---

## ◈ Credits & Acknowledgments

* **[Discord-Legacy-Patcher](https://github.com/Jazzzny/Discord-Legacy-Patcher)** by **Jazzzny** — This project is a CLI evolution of the original research and patching logic provided by Jazzzny. Huge shoutout for making the first project that paved the way for legacy Discord support.
* Developed and enhanced with a TUI wrapper by **N1-TR0**.

---

## 🤝 Contributing & Support

If you encounter issues with specific hardware models or macOS versions, please open an issue on the GitHub repository.

---

> **Disclaimer:** This project is not affiliated with Discord Inc. It is a community tool intended to extend the life of older hardware. Use at your own risk.
