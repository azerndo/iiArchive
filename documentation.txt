# iArchive - Technical Documentation

## Overview

iArchive is a desktop archive management application built with PyQt6 that provides a graphical interface for creating, extracting, and managing compressed archives. The application supports multiple archive formats including ZIP, TAR, GZIP, BZIP2, XZ, and provides basic support for 7Z and RAR formats.

## Architecture

The application follows a modular design pattern with three main functional areas accessed through a tabbed interface. Each tab handles a specific workflow: archive creation, extraction, and file management.

### Core Components

1. **Main Window** (`IArchiveApp`): Central application controller managing the UI and coordinating operations
2. **Custom Widgets**: Specialized UI components for drag-and-drop functionality
3. **Worker Threads**: Background processing for intensive operations like checksum calculation
4. **Format Handlers**: Modular archive creation and extraction logic

## Technical Implementation

### UI Framework and Theming

The application uses PyQt6 as its GUI framework. A custom color scheme creates a warm, modern aesthetic using brown and orange tones. The stylesheet is defined globally in the `STYLESHEET` constant and applies consistent styling across all widgets.

Key design decisions:
- Colors defined in a dictionary for easy modification
- Global stylesheet prevents style inconsistencies
- Custom focus states and hover effects improve user feedback
- Border radius on buttons and inputs creates a modern look

### Format Configuration

Archives are handled through a configuration dictionary that defines properties for each format:

```python
FORMAT_CONFIG = {
    "Tar":   {"ext": ".tar", "type": "archive", "multi": True},
    "Zip":   {"ext": ".zip", "type": "compressed_archive", "multi": True},
    # ... additional formats
}
```

This design allows the application to:
- Validate single vs. multiple file operations
- Generate appropriate file extensions
- Route operations to correct handlers

### Tab 1: Archive Creation

The creation tab implements a drag-and-drop workflow for adding files to archives.

#### Custom List Widget

`DragDropListWidget` extends `QListWidget` to accept file drops from the system file manager. The implementation overrides three drag-and-drop methods:

- `dragEnterEvent`: Validates that dropped content contains file URLs
- `dragMoveEvent`: Continues validation during drag motion
- `dropEvent`: Processes the dropped files

Files are deduplicated before adding to prevent accidental duplicates. The widget also supports keyboard shortcuts (Delete/Backspace) to remove selected items.

#### Multi-Strategy ZIP Creation

The ZIP creation logic implements three fallback strategies to handle different scenarios:

**Strategy 1: pyzipper Library**
When password protection is requested and the pyzipper library is available, it's used for AES encryption:

```python
with pyzipper.AESZipFile(dest, 'w', compression=zipfile.ZIP_DEFLATED, 
                         encryption=pyzipper.WZ_AES) as zf:
    zf.setpassword(pwd.encode('utf-8'))
```

**Strategy 2: System ZIP Command**
If pyzipper is unavailable, the application falls back to the system's native `zip` command:

```python
cmd = ["zip", "-P", pwd, "-r", dest] + files
subprocess.run(cmd, check=True)
```

This approach has benefits and drawbacks:
- Benefit: Works without additional Python dependencies
- Drawback: Requires system utilities to be installed
- Implementation: Checks for command availability before execution

**Strategy 3: Standard zipfile**
For unencrypted archives, Python's built-in zipfile module is used as it requires no external dependencies.

#### Recursive Archiving

When the "Recursively archive sub-folders" option is enabled, the application walks directory trees using `os.walk()`. For each file found:

1. Check if it matches the exclusion pattern
2. Calculate relative path from the base directory
3. Add to archive with preserved directory structure

The `arcname` parameter ensures files maintain their folder hierarchy within the archive.

### Tab 2: Extraction

The extraction tab reverses the archiving process, supporting multiple compressed formats.

#### Format Detection

Archive type is determined by file extension rather than magic number detection:

```python
if src.endswith('.zip'):
    # ZIP extraction logic
elif src.endswith('.tar'):
    # TAR extraction logic
```

While magic number detection would be more robust, extension-based detection is simpler and sufficient for user-selected files.

#### Encryption Handling

A specific try-catch block handles encrypted ZIP files:

```python
except RuntimeError as e:
    if "encrypted" in str(e) or "Bad password" in str(e):
        QMessageBox.warning(self, "Encrypted Zip", 
            "This file is encrypted. Please use macOS Finder to extract it.")
```

This was implemented because:
1. Python's zipfile module cannot extract password-protected archives without the password
2. Rather than prompt for a password (which adds complexity), the application directs users to system tools
3. This maintains simplicity while acknowledging the limitation

#### Exclusion Filtering

Files can be excluded during extraction using the exclusion field. The `_should_exclude` helper function checks if a filename ends with the specified extension. Files matching the pattern are filtered from the member list before extraction.

### Tab 3: Archive Management

The management tab provides inspection and modification capabilities for existing archives.

#### Asynchronous Checksum Calculation

Checksums are calculated in a separate thread to prevent UI freezing:

```python
class ChecksumWorker(QThread):
    result = pyqtSignal(str)
    
    def run(self):
        sha256_hash = hashlib.sha256()
        with open(self.filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
```

The worker emits a signal when complete, updating the UI from the main thread. This pattern prevents blocking operations on large files.

#### File Listing

Archives are opened in read mode and their contents enumerated:

- ZIP files use `ZipFile.infolist()` to get file metadata
- TAR files use `TarFile.getmembers()` for member information

The table displays filename, size, and entry type for each contained file.

#### Append Functionality

Files can be added to existing archives using append mode:

```python
with tarfile.open(arc_path, 'a') as tf:
    tf.add(f_to_add, arcname=os.path.basename(f_to_add))
```

This opens the archive in append mode ('a'), which adds new members without rewriting existing content. The same approach works for ZIP files using `ZipFile`.

#### Delete Implementation

Deleting files from an archive requires recreation because archive formats don't support in-place deletion:

1. Create a temporary archive
2. Copy all members except the one being deleted
3. Replace original with temporary archive

This is why deletion is only enabled for uncompressed TAR files - compressed formats would require decompression, modification, and recompression, which is significantly more complex.

## Design Decisions

### Why Three Archive Creation Strategies?

The multi-strategy approach for ZIP creation emerged from real-world constraints:

1. pyzipper provides the best encryption but requires installation
2. System commands work universally on Unix systems
3. Standard library ensures basic functionality always works

This layered fallback ensures the application works in various environments.

### Why Disable Deletion for Compressed Archives?

Modifying compressed archives (tar.gz, etc.) requires:
1. Decompressing the entire archive
2. Removing the target file
3. Recompressing everything

This is expensive and error-prone. The UI clearly indicates this limitation by disabling the button and changing its label to "Delete Disabled (Compressed)".

### Why Check Format When Adding Files?

Single-file compression formats (GZIP, BZIP2, XZ) only compress one file. The format change handler prevents users from adding multiple files to these formats:

```python
def on_format_changed(self, text):
    cfg = FORMAT_CONFIG[text]
    if not cfg["multi"] and self.file_list.count() > 1:
        QMessageBox.warning(self, "Restriction", 
            f"{text} only supports single file compression.")
        self.file_list.clear()
```

This prevents user confusion and operation failures.

### Why Use System Icons?

The application uses system-provided icons for files and folders:

```python
icon_provider = QApplication.style()
if os.path.isdir(path):
    icon = icon_provider.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
```

This ensures icons match the user's operating system theme and reduces bundle size by not including custom icon files.

## Error Handling Strategy

The application uses defensive programming throughout:

1. **Input Validation**: Checks for empty file lists and missing destinations before processing
2. **Exception Catching**: Broad try-catch blocks around archive operations with user-friendly error messages
3. **Graceful Degradation**: Falls back to alternative methods when preferred approaches fail
4. **User Feedback**: Modal dialogs inform users of errors with actionable information

## Performance Considerations

### File Reading in Chunks

Large file operations (compression, checksums) read data in 4KB chunks:

```python
for byte_block in iter(lambda: f.read(4096), b""):
    sha256_hash.update(byte_block)
```

This prevents loading entire files into memory, allowing the application to handle files larger than available RAM.

### Thread Usage

Only checksum calculation uses threading because:
- It's the most time-consuming operation for large files
- Archive operations are already I/O bound (threading wouldn't help)
- Fewer threads reduces complexity and potential race conditions

## Dependencies

### Required
- PyQt6: GUI framework
- Python standard library: tarfile, zipfile, gzip, bz2, lzma, hashlib

### Optional
- pyzipper: Enhanced ZIP encryption support
- System utilities: zip command for password-protected archives

The application gracefully handles missing optional dependencies by either falling back to alternatives or clearly communicating limitations to users.

## Future Enhancement Possibilities

Several features were considered but not implemented in the current version:

1. **Progress Bars**: Would require threading all archive operations and progress callbacks
2. **Archive Preview**: Could show first few bytes or preview images before extraction
3. **Batch Operations**: Process multiple archives in sequence
4. **Custom Compression Levels**: Expose compression quality settings
5. **Archive Comparison**: Diff two archives to see differences

These were omitted to maintain code simplicity and focus on core functionality.

## Conclusion

iArchive demonstrates practical application of GUI programming concepts, file I/O operations, and user experience design. The codebase prioritizes reliability and clarity over advanced features, making it maintainable and extensible for future development.