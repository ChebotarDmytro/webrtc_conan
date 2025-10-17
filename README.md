# WebRTC Conan Package

Conan 2.x recipe for building and packaging Google's WebRTC library for Linux.

## Overview

This package provides a monolithic WebRTC library (`libwebrtc.a`) built from Google's WebRTC source using depot_tools and the native GN/Ninja build system. It's designed for standalone applications that need WebRTC functionality without the complexity of Chrome's build infrastructure.

**Version**: 7151 (Milestone 137, 2024)

## Features

- ✅ Monolithic static library (single `libwebrtc.a`)
- ✅ Includes all necessary headers (api, rtc_base, p2p, etc.)
- ✅ Bundles third-party headers (abseil, libyuv)
- ✅ Supports Debug and RelWithDebInfo build types
- ✅ Uses system Clang-21 compiler
- ✅ Optimized build configuration (no PGO complexity)
- ✅ H.264 codec support via FFmpeg
- ✅ Automatic ranlib execution for symbol indexing

## Requirements

### System Dependencies

```bash
sudo apt update
sudo apt install -y \
  git python3 python3-pip \
  libgtk-3-dev libx11-dev libxss1 libnss3-dev libasound2-dev \
  libglu1-mesa-dev libxrandr-dev libxcomposite-dev libxdamage-dev \
  libxfixes-dev libxext-dev clang-21 lld-21
```

### Conan

- Conan >= 2.0
- CMake >= 3.20 (provided by Conan if needed)

### Disk Space

- Source: ~10 GB
- Debug build: ~15 GB  
- RelWithDebInfo build: ~10 GB
- **Total**: Plan for 40-50 GB free space

## Quick Start

```bash
# 1. Fetch WebRTC source (run once)
conan source .

# 2. Build the package
conan build . -s build_type=Debug

# 3. Export to Conan cache
conan export-pkg . -s build_type=Debug

# Optional: Build RelWithDebInfo
conan build . -s build_type=RelWithDebInfo
conan export-pkg . -s build_type=RelWithDebInfo
```

## Usage in Your Project

### conanfile.py

```python
from conan import ConanFile

class MyProjectConan(ConanFile):
    requires = "webrtc/7151"
    generators = "CMakeDeps", "CMakeToolchain"
    settings = "os", "compiler", "build_type", "arch"
```

### CMakeLists.txt

```cmake
find_package(webrtc REQUIRED)

add_executable(myapp main.cpp)
target_link_libraries(myapp PRIVATE webrtc::webrtc)
```

### Build Your Project

```bash
conan install . --output-folder=build --build=missing -s build_type=Debug
conan build . -s build_type=Debug
```

## Package Options

| Option | Default | Description |
|--------|---------|-------------|
| `shared` | False | Build shared library (not recommended) |
| `fPIC` | True | Position independent code |
| `with_h264` | True | Enable H.264 codec support |
| `with_vp8` | True | Enable VP8 codec |
| `with_vp9` | True | Enable VP9 codec |
| `enable_protobuf` | False | Enable protobuf support |
| `enable_rtti` | False | Enable RTTI (not recommended) |

### Example: Custom Options

```bash
# Build without H.264
conan build . -o webrtc/*:with_h264=False -s build_type=Debug

# Build with RTTI
conan build . -o webrtc/*:enable_rtti=True -s build_type=Debug
```

## Build Types

### Debug

**Configuration**:
```python
is_debug = true
is_official_build = false
symbol_level = 2  # Full symbols
```

**Characteristics**:
- No optimization (`-O0`)
- Full debug symbols
- Assertions enabled
- Large binary (~500MB)
- Best for development and debugging

**Use when**:
- Debugging crashes
- Stepping through WebRTC code
- Understanding WebRTC internals

### RelWithDebInfo

**Configuration**:
```python
is_debug = false
is_official_build = false  # Important: uses -O2, not -O3+PGO
symbol_level = 1           # Minimal symbols
chrome_pgo_phase = 0       # Disable PGO
```

**Characteristics**:
- Optimized with `-O2` (automatic)
- Minimal debug symbols
- Assertions disabled
- Medium binary (~300MB)
- **4-5x faster than Debug**
- Best for development and performance testing

**Use when**:
- Performance testing
- Profiling
- Production-like testing
- Still need crash debugging capability

### Why Not Release?

Release builds with full optimization (`-O3` + PGO) require:
- Chrome's PGO profile data (not available in standalone builds)
- Multiple build passes
- Chrome test infrastructure

For standalone applications, **RelWithDebInfo provides 95% of the performance** without the complexity.

## Build Process

### Phase 1: Source (conan source .)

**What it does**:
1. Clones depot_tools (~100 MB)
2. Creates `.gclient` configuration
3. Runs `gclient sync` to download WebRTC source (~10 GB)
4. Checks out branch `branch-heads/7151`
5. Syncs all dependencies

**Time**: 30-60 minutes (network dependent)

**Disk usage**: ~10 GB

**Run once**, unless you need to update the source.

### Phase 2: Build (conan build .)

**What it does**:
1. Configures build with GN (generates Ninja files)
2. Builds WebRTC with Ninja (~2000+ targets)
3. Creates monolithic `libwebrtc.a`
4. Runs `ranlib` on all static libraries

**Time**: 2-4 hours (first build), 5-15 minutes (incremental)

**Disk usage**: 
- Debug: ~15 GB
- RelWithDebInfo: ~10 GB

**Parallelization**: Uses all CPU cores by default

### Phase 3: Package (conan export-pkg .)

**What it does**:
1. Copies headers to package folder
   - Main API headers (api/, rtc_base/, p2p/, etc.)
   - Third-party headers (abseil, libyuv)
2. Copies `libwebrtc.a` to package folder
3. Generates package metadata
4. Installs to Conan cache

**Time**: 1-2 minutes

**Disk usage**: ~500 MB in Conan cache per build type

## GN Build Arguments

The package uses these GN arguments:

### Common (All Build Types)

```python
target_os = "linux"
target_cpu = "x64"
clang_base_path = "/usr/lib/llvm-21"
clang_version = "21"
clang_use_chrome_plugins = false
treat_warnings_as_errors = false
is_component_build = false      # Monolithic library
rtc_include_tests = false
rtc_build_examples = false
rtc_build_tools = false
rtc_use_h264 = true
ffmpeg_branding = "Chrome"
use_rtti = false
use_custom_libcxx = false       # Use system libc++
rtc_enable_protobuf = false
```

### Debug Specific

```python
is_debug = true
is_official_build = false
symbol_level = 2
```

### RelWithDebInfo Specific

```python
is_debug = false
is_official_build = false       # Critical: avoid PGO
symbol_level = 1
chrome_pgo_phase = 0            # Explicitly disable PGO
```

### Why is_official_build = false?

Setting `is_official_build=true`:
- ✅ Enables `-O3` optimization
- ❌ Enables PGO (Profile-Guided Optimization)
- ❌ Requires Chrome `.profdata` files
- ❌ Needs multiple build passes
- ❌ Can cause `SIGILL` (illegal instruction) errors

Setting `is_official_build=false`:
- ✅ Uses safe `-O2` optimization (when `is_debug=false`)
- ✅ No PGO complexity
- ✅ No Chrome dependencies
- ✅ Works on all x86_64 systems
- ✅ Still very fast (95% of -O3 performance)

**For standalone builds, always use `is_official_build=false`.**

## Package Contents

### Headers

```
include/
├── api/                      # Main WebRTC API
├── rtc_base/                 # Base utilities
├── p2p/                      # P2P networking
├── pc/                       # PeerConnection
├── media/                    # Media engine
├── modules/                  # Audio/video modules
├── common_video/             # Video utilities
├── common_audio/             # Audio utilities
├── call/                     # Call API
├── video/                    # Video API
├── audio/                    # Audio API
├── system_wrappers/          # System abstractions
├── logging/                  # Logging
├── absl/                     # Abseil (bundled)
└── libyuv/                   # YUV conversion (bundled)
```

### Libraries

```
lib/
└── libwebrtc.a              # Monolithic static library (~300-500 MB)
```

### System Libraries (Linked Automatically)

- `dl` - Dynamic loading
- `pthread` - Threading
- `rt` - Real-time extensions
- `X11` - X11 display
- `Xext` - X11 extensions
- `Xdamage` - X11 damage extension
- `Xfixes` - X11 fixes extension
- `Xcomposite` - X11 composite extension
- `Xrandr` - X11 RandR extension

## Workspace Layout

The package uses an in-place build strategy to save disk space:

```
webrtc/                       # Source folder (this directory)
├── conanfile.py              # This recipe
├── depot_tools/              # Created by conan source
│   ├── gclient
│   ├── gn
│   └── ninja
└── webrtc_checkout/          # Created by conan source
    ├── .gclient
    └── src/                  # WebRTC source
        ├── api/
        ├── modules/
        ├── out/
        │   ├── Debug/
        │   │   └── obj/
        │   │       └── libwebrtc.a
        │   └── RelWithDebInfo/
        │       └── obj/
        │           └── libwebrtc.a
        └── third_party/
```

**Note**: Using `conan create` would copy everything twice, wasting 40+ GB. Use the `source → build → export-pkg` workflow instead.

## Troubleshooting

### Build Errors

#### Error: `FileNotFoundError: chrome/build/linux.pgo.txt`

**Cause**: PGO is enabled but profile files are missing.

**Solution**: Already fixed in this recipe. If you modified GN args, ensure:
```python
is_official_build = false
chrome_pgo_phase = 0
```

#### Error: `Unexpected token '-'` in GN args

**Cause**: Invalid GN argument syntax (e.g., `optimize_max=-O2`).

**Solution**: Don't add custom optimization flags. WebRTC handles optimization automatically based on `is_debug` and `is_official_build`.

#### Error: `SIGILL (Illegal Instruction)` at runtime

**Cause**: PGO or aggressive optimizations generated CPU-specific instructions.

**Solution**: Already fixed in this recipe with `is_official_build=false` and `chrome_pgo_phase=0`.

#### Error: `archive has no index`

**Cause**: Static libraries missing symbol index.

**Solution**: Already fixed - recipe runs `ranlib` automatically during build.

#### Error: `clang++-21: not found`

**Cause**: Clang-21 not installed.

**Solution**:
```bash
sudo apt install clang-21 lld-21
```

#### Error: `gclient: command not found`

**Cause**: depot_tools not in PATH or not downloaded.

**Solution**: Run `conan source .` first, which downloads depot_tools.

### Runtime Issues

#### Application crashes in WebRTC code

**Debug**:
```bash
# Rebuild with Debug symbols
conan build . -s build_type=Debug
conan export-pkg . -s build_type=Debug --force

# Rebuild your app with Debug
conan install . --build=missing -s build_type=Debug
conan build . -s build_type=Debug

# Run with debugger
gdb ./build/Debug/myapp
```

#### Performance issues

**Solution**: Use RelWithDebInfo, not Debug:
```bash
conan build . -s build_type=RelWithDebInfo
conan export-pkg . -s build_type=RelWithDebInfo
```

RelWithDebInfo is 4-5x faster than Debug.

## Advanced Usage

### Using a Different WebRTC Branch

Edit `conanfile.py`:
```python
class WebRTCConan(ConanFile):
    name = "webrtc"
    version = "6099"  # Change version
```

Then rebuild:
```bash
rm -rf depot_tools/ webrtc_checkout/
conan source .
conan build . -s build_type=Debug
conan export-pkg . -s build_type=Debug
```

**Available branches**: https://chromiumdash.appspot.com/branches

### Custom GN Arguments

Edit the `_get_gn_args()` method:

```python
def _get_gn_args(self):
    args = []
    # ... existing args ...
    
    # Add your custom args
    args.append('proprietary_codecs=true')
    args.append('rtc_use_h265=true')  # If available
    
    return args
```

### Building for ARM

Edit GN args for target CPU:

```python
# In _get_gn_args()
args.append('target_cpu="arm64"')  # For ARM64
# or
args.append('target_cpu="arm"')    # For ARM32
```

Then:
```bash
conan build . -s arch=armv8 -s build_type=RelWithDebInfo
```

### Shared Library Build

```bash
conan build . -o shared=True -s build_type=RelWithDebInfo
```

**Note**: Shared library support is experimental. Static linking is recommended.

## Verification

### Check Package Installation

```bash
# List installed packages
conan list webrtc/7151

# Show package details
conan list webrtc/7151:*

# Check package folder
conan cache path webrtc/7151
```

### Verify Library Contents

```bash
# Find package location
WEBRTC_PATH=$(conan cache path webrtc/7151)

# List headers
ls -R $WEBRTC_PATH/p/include/

# Check library
ls -lh $WEBRTC_PATH/p/lib/libwebrtc.a

# Check symbols
nm -C $WEBRTC_PATH/p/lib/libwebrtc.a | grep CreatePeerConnection
```

### Test Integration

Create a minimal test project:

```cpp
// test.cpp
#include "api/create_peerconnection_factory.h"
#include <iostream>

int main() {
    auto factory = webrtc::CreatePeerConnectionFactory(
        nullptr, nullptr, nullptr, nullptr, nullptr, nullptr,
        nullptr, nullptr, nullptr, nullptr, nullptr);
    
    if (factory) {
        std::cout << "WebRTC factory created successfully!" << std::endl;
        return 0;
    }
    return 1;
}
```

```cmake
# CMakeLists.txt
cmake_minimum_required(VERSION 3.20)
project(test)

find_package(webrtc REQUIRED)

add_executable(test test.cpp)
target_link_libraries(test PRIVATE webrtc::webrtc)
```

```bash
conan install . --output-folder=build --build=missing -s build_type=Debug
cd build && cmake .. -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake
cmake --build .
./test
```

## Performance Notes

### Build Times (Typical)

| Operation | First Time | Incremental |
|-----------|-----------|-------------|
| `conan source` | 30-60 min | 1 min |
| `conan build` Debug | 2-4 hours | 5-15 min |
| `conan build` RelWithDebInfo | 2-4 hours | 5-15 min |
| `conan export-pkg` | 1-2 min | 1-2 min |

**Tips**:
- Use `-j<N>` to limit parallel jobs if memory-constrained
- ccache can speed up rebuilds (set `CC_WRAPPER=ccache` in GN args)

### Runtime Performance

| Build Type | Relative Speed | Binary Size |
|------------|---------------|-------------|
| Debug | 1x (baseline) | ~500 MB |
| RelWithDebInfo | 4-5x | ~300 MB |
| Official (Chrome) | 5-6x | ~250 MB |

**Verdict**: RelWithDebInfo provides 90-95% of official build performance without PGO complexity.

## Cleaning Up

### Remove Build Artifacts

```bash
# Remove build outputs (keep source)
rm -rf webrtc_checkout/src/out/

# Remove from Conan cache
conan remove webrtc/7151 -c

# Complete cleanup
rm -rf depot_tools/ webrtc_checkout/
```

### Disk Space Reclamation

After building both Debug and RelWithDebInfo:
```bash
# Keep only RelWithDebInfo
rm -rf webrtc_checkout/src/out/Debug/

# Remove intermediate objects (risky - can't rebuild incrementally)
find webrtc_checkout/src/out/RelWithDebInfo/obj -name "*.o" -delete
```

## Contributing

### Testing Changes

```bash
# Test Debug build
conan remove webrtc/7151 -c
conan source .
conan build . -s build_type=Debug
conan export-pkg . -s build_type=Debug

# Test RelWithDebInfo build
conan build . -s build_type=RelWithDebInfo
conan export-pkg . -s build_type=RelWithDebInfo

# Test in consumer project
cd ../webrtc_simple_example
rm -rf build
conan install . --output-folder=build --build=missing -s build_type=Debug
conan build . -s build_type=Debug
./build/Debug/webrtcexample
```

### Modifying GN Args

1. Edit `_get_gn_args()` method
2. Clean build: `rm -rf webrtc_checkout/src/out/`
3. Rebuild: `conan build . -s build_type=Debug`
4. Verify: `gn args webrtc_checkout/src/out/Debug --short`

## Resources

- [WebRTC Source](https://webrtc.googlesource.com/src/)
- [WebRTC Native API Docs](https://webrtc.github.io/webrtc-org/native-code/native-apis/)
- [depot_tools](https://commondatastorage.googleapis.com/chrome-infra-docs/flat/depot_tools/docs/html/depot_tools.html)
- [GN Reference](https://gn.googlesource.com/gn/+/main/docs/reference.md)
- [Conan Documentation](https://docs.conan.io/2/)
- [WebRTC Issue Tracker](https://issues.webrtc.org/)

## License

WebRTC is licensed under a BSD-style license by Google Inc. See the WebRTC source repository for details.

This Conan recipe is provided as-is for packaging purposes.

---

**Version**: 7151 (M137)  
**Conan**: 2.x  
**Platform**: Linux x86_64  
**Compiler**: Clang 21  
**Last Updated**: 2024
