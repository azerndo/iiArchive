# 📦 iArchive

![iArchive Logo](assets/logo.png)

**iArchive** is a minimalist, warm-themed desktop application built with **Python** and **PyQt6**. It creates, manages, and extracts various archive and compression formats with a focus on simplicity and ease of use.

---

## ✨ Features

### 1. Archiving & Compression
* **Supported Formats:**
  * **Archives:** `.tar`, `.zip`
  * **Compression Only:** `.gz`, `.bz2`, `.xz`
  * **External Formats:** `.7z`, `.rar` (Requires external configuration)
* **Recursive Options:** Choose whether to include sub-directories or just the root folder files.
* **Drag & Drop:** Simply drag files into the window to add them to the list.

### 2. Extraction (Unzip)
* Extracts files from `.zip`, `.tar`, `.tar.gz`, and `.gz`.
* **Smart Exclusion:** Filter out specific file types (e.g., `.DS_Store`, `.tmp`) during extraction.

### 3. Archive Management
* **Inspect:** View the contents of an archive without extracting it.
* **Checksum:** Automatically calculates **SHA-256** checksums for file verification.
* **Modify:**
  * **Append:** Add new files to existing `.tar` or `.zip` archives.
  * **Delete:** Remove specific files from `.tar` archives (Repacking supported).

---

## Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/azerndo/iArchive.git]
    cd iarchive
    ```

2.  **Create a virtual environment (Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

To run the application from source:

```bash
python3 src/main.py
