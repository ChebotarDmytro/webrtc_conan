from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, save, chdir
from conan.tools.scm import Git
from conan.tools.layout import basic_layout
import os
import textwrap

required_conan_version = ">=2.0"


class WebRTCConan(ConanFile):
    name = "webrtc"
    version = "7151"  # m137
    license = "BSD-3-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://webrtc.googlesource.com/src"
    description = "WebRTC is a free, open-source project for real-time communications"
    topics = ("webrtc", "real-time", "communication", "video", "audio")
    
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_h264": [True, False],
        "with_vp8": [True, False],
        "with_vp9": [True, False],
        "enable_protobuf": [True, False],
        "enable_rtti": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_h264": True,
        "with_vp8": True,
        "with_vp9": True,
        "enable_protobuf": False,
        "enable_rtti": False,
    }
    
    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("This recipe only supports Linux")
        
        # Only allow Debug and RelWithDebInfo
        valid_build_types = ["Debug", "RelWithDebInfo"]
        if str(self.settings.build_type) not in valid_build_types:
            raise ConanInvalidConfiguration(
                f"Build type '{self.settings.build_type}' is not supported. "
                f"Only {valid_build_types} are allowed."
            )
    
    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
    
    def layout(self):
        # For local workflow (conan install/build/export-pkg):
        # Keep source and build in workspace to save disk space
        # 
        # For conan create: it will copy anyway, but that's unavoidable
        # Use export-pkg workflow instead to save 3-4GB disk space
        self.folders.source = "."
        self.folders.build = "."
    
    def requirements(self):
        # Note: WebRTC bundles most dependencies
        pass
    
    def build_requirements(self):
        # ninja is provided by depot_tools, no need for conan package
        pass

    def source(self):
        # Workspace structure:
        # workspace/
          # └── webrtc_conan (source_folder)
             # ├── depot_tools/
             # ├── webrtc_checkout/
             # │   ├── .gclient
             # │   └── src/
             # └── conanfile.py
        
        depot_tools_path = self._get_depot_tools_path()
        
        # Check if depot_tools already exists
        if os.path.exists(depot_tools_path):
            self.output.info(f"depot_tools already exists at {depot_tools_path}, skipping clone...")
        else:
            self.output.info("Cloning depot_tools into workspace...")
            git = Git(self)
            git.clone(
                url="https://chromium.googlesource.com/chromium/tools/depot_tools.git",
                target=depot_tools_path,
                args=["--depth", "1"]
            )
        
        # Set up environment for gclient
        depot_tools_abs = os.path.abspath(depot_tools_path)
        env_path = f"{depot_tools_abs}:{os.environ.get('PATH', '')}"

        # Bootstrap depot_tools (initializes Python and tools)
        self.output.info("Bootstrapping depot_tools...")
        self.run(f'PATH="{env_path}" gclient --version', env="conanbuild")
        
        # Create .gclient configuration inside webrtc_checkout
        gclient_config = textwrap.dedent(f"""
            solutions = [
              {{
                "name": "src",
                "url": "https://webrtc.googlesource.com/src.git",
                "deps_file": "DEPS",
                "managed": False,
                "custom_deps": {{}},
              }},
            ]
            target_os = ["linux"]
        """)

        checkout_path = self._get_webrtc_checkout_path()

        # Create webrtc_checkout folder if it doesn't exist
        os.makedirs(checkout_path, exist_ok=True)

        gclient_file = os.path.join(checkout_path, ".gclient")
        save(self, gclient_file, gclient_config)
        self.output.info(f"Created .gclient config at {gclient_file}")
        
        # Run gclient sync inside webrtc_checkout folder
        src_path = os.path.join(checkout_path, "src")
        
        # Check if WebRTC source already exists
        if os.path.exists(src_path) and os.path.exists(os.path.join(src_path, ".git")):
            self.output.info(f"WebRTC source already exists at {src_path}, skipping initial sync...")
        else:
            self.output.info("Running gclient sync inside webrtc_checkout (this may take a while)...")
            with chdir(self, checkout_path):
                # Use gclient command directly
                self.run(f'PATH="{env_path}" gclient sync --nohooks --no-history', env="conanbuild")
            
            # Checkout specific branch/milestone
            with chdir(self, src_path):
                branch = f"branch-heads/{self.version}"
                
                # Check current branch
                try:
                    result = self.run("git rev-parse --abbrev-ref HEAD", env="conanbuild")
                    current_branch = result.strip() if hasattr(result, 'strip') else ""
                    
                    if current_branch == branch or current_branch.endswith(f"/{branch}"):
                        self.output.info(f"Already on branch {branch}, skipping checkout...")
                    else:
                        self.output.info(f"Checking out branch {branch}...")
                        self.run(f"git fetch origin refs/{branch}:{branch}", env="conanbuild")
                        self.run(f"git checkout {branch}", env="conanbuild")
                except Exception:
                    # If we can't determine branch, just checkout
                    self.output.info(f"Checking out branch {branch}...")
                    self.run(f"git fetch origin refs/{branch}:{branch}", env="conanbuild")
                    self.run(f"git checkout {branch}", env="conanbuild")
            
            # Re-sync after checkout inside webrtc_checkout
            with chdir(self, checkout_path):
                self.run(f'PATH="{env_path}" gclient sync -D --force --reset', env="conanbuild")
    
    def _get_depot_tools_path(self):
        return os.path.join(self.source_folder, "depot_tools")
    
    def _get_src_path(self):
        return os.path.join(self.source_folder, "webrtc_checkout", "src")

    def _get_webrtc_checkout_path(self):
        return os.path.join(self.source_folder, "webrtc_checkout")
    
    def _get_build_type_name(self):
        """Map Conan build_type to GN output directory name"""
        return str(self.settings.build_type)
    
    def _get_gn_args(self):
        args = []
        
        # Target OS and CPU
        args.append('target_os="linux"')
        
        arch_map = {
            "x86_64": "x64",
            "x86": "x86",
            "armv8": "arm64",
            "armv7": "arm",
        }
        arch_str = str(self.settings.arch)
        if arch_str in arch_map:
            args.append(f'target_cpu="{arch_map[arch_str]}"')

        # Compiler
        args.append('clang_base_path = "/usr/lib/llvm-21"')
        args.append('clang_version = "21"')
        args.append('clang_use_chrome_plugins = false')

        # Warnings
        args.append('treat_warnings_as_errors = false')
        
        # Build type specific settings
        build_type = str(self.settings.build_type)
        
        if build_type == "Debug":
            args.append('is_debug=true')
            args.append('is_official_build=false')
            args.append('symbol_level=2')  # Full debug symbols
        elif build_type == "RelWithDebInfo":
            args.append('is_debug=false')
            args.append('is_official_build=false')  # Don't use official build - it enables PGO
            args.append('symbol_level=1')  # Minimal debug symbols for debugging
            # Disable PGO explicitly (Profile-Guided Optimization requires Chrome profiles)
            args.append('chrome_pgo_phase=0')
        
        # Monolithic build (creates single libwebrtc.a or libwebrtc.so)
        args.append('is_component_build=false')
        
        # Tests and examples
        args.append('rtc_include_tests=false')
        args.append('rtc_build_examples=false')
        args.append('rtc_build_tools=false')
        
        # H.264 support
        args.append(f'rtc_use_h264={str(self.options.with_h264).lower()}')
        if self.options.with_h264:
            args.append('ffmpeg_branding="Chrome"')
        
        # VP8/VP9 codecs
        if not self.options.with_vp8:
            args.append('rtc_use_vp8=false')
        if not self.options.with_vp9:
            args.append('rtc_use_vp9=false')
        
        # RTTI and libcxx
        args.append(f'use_rtti={str(self.options.enable_rtti).lower()}')
        args.append('use_custom_libcxx=false')

        # Protobuf
        args.append(f'rtc_enable_protobuf={str(self.options.enable_protobuf).lower()}')

        # PGO (Profile-Guided Optimization) data for Chrome
        args.append('chrome_pgo_phase=0')
        
        return args
    
    def generate(self):
        pass
    
    def build(self):
        depot_tools = self._get_depot_tools_path()
        src_path = self._get_src_path()
        depot_tools_abs = os.path.abspath(depot_tools)
        env_path = f"{depot_tools_abs}:{os.environ.get('PATH', '')}"
        
        # Path to gn binary (from depot_tools)
        gn_path = os.path.join(depot_tools_abs, "gn")
        
        # Build directory - use build type name
        build_type_name = self._get_build_type_name()
        build_dir = os.path.join(src_path, "out", build_type_name)
        
        with chdir(self, src_path):
            # Generate build files with gn
            gn_args = " ".join(self._get_gn_args())
            self.output.info(f"Building for: {build_type_name}")
            self.output.info(f"GN args: {gn_args}")

            # Escape quotes properly for shell - use single quotes to preserve inner double quotes
            self.run(f"PATH=\"{env_path}\" {gn_path} gen {build_dir} --args='{gn_args}'", env="conanbuild")
            
            # Build with ninja (from depot_tools)
            ninja_path = os.path.join(depot_tools_abs, "ninja")
            
            # Build default target - with is_component_build=false, 
            # this creates monolithic libwebrtc.a or libwebrtc.so
            self.output.info(f"Building monolithic WebRTC library ({build_type_name})...")
            self.run(f'PATH="{env_path}" {ninja_path} -C {build_dir} -j{os.cpu_count()}', env="conanbuild")

    def package(self):
        src_path = self._get_src_path()
        build_type_name = self._get_build_type_name()
        build_dir = os.path.join(src_path, "out", build_type_name)
        obj_dir = os.path.join(build_dir, "obj")
        self.output.info(f"Packaging from build dir: {build_dir}")

        # License
        copy(self, "LICENSE",
             src=src_path,
             dst=os.path.join(self.package_folder, "licenses"))

        # Headers - main API
        for subdir in ["api", "rtc_base", "p2p", "pc", "media", "modules", "common_video", "common_audio",
                       "call", "video", "audio", "system_wrappers", "logging"]:
            src_dir = os.path.join(src_path, subdir)
            if os.path.exists(src_dir):
                copy(self, "*.h",
                     src=src_dir,
                     dst=os.path.join(self.package_folder, "include", subdir),
                     keep_path=True)

        # Copy third_party headers that WebRTC exposes
        third_party = os.path.join(src_path, "third_party")

        absl_lib_path = os.path.join(third_party, "abseil-cpp/absl")
        if os.path.exists(absl_lib_path):
            copy(self, "*.h",
                 src=absl_lib_path,
                 dst=os.path.join(self.package_folder, "include", os.path.basename(absl_lib_path)),
                 keep_path=True)
            copy(self, "*.inc",
                 src=absl_lib_path,
                 dst=os.path.join(self.package_folder, "include", os.path.basename(absl_lib_path)),
                 keep_path=True)

        libyuv_lib_path = os.path.join(third_party, "libyuv/include")
        if os.path.exists(libyuv_lib_path):
            copy(self, "*.h",
                 src=libyuv_lib_path,
                 dst=os.path.join(self.package_folder, "include"),
                 keep_path=True)

        # Copy monolithic library (created by is_component_build=false)
        if self.options.shared:
            # Shared monolithic library
            copy(self, "libwebrtc.so*",
                 src=obj_dir,
                 dst=os.path.join(self.package_folder, "lib"),
                 keep_path=False)
        else:
            # Static monolithic library
            copy(self, "libwebrtc.a",
                 src=obj_dir,
                 dst=os.path.join(self.package_folder, "lib"),
                 keep_path=False)

            # Verify the monolithic library exists
            lib_path = os.path.join(self.package_folder, "lib", "libwebrtc.a")
            if not os.path.exists(lib_path):
                self.output.warning(f"Monolithic library not found at {lib_path}")
                self.output.info(f"Checking build directory: {obj_dir}")
                import glob
                libs = glob.glob(os.path.join(obj_dir, "*.a"))
                if libs:
                    self.output.info(f"Found libraries: {libs}")
                else:
                    self.output.warning("No .a libraries found in build directory")
    
    def package_info(self):
        # Single monolithic library
        self.cpp_info.libs = ["webrtc"]
        
        # Include directories
        self.cpp_info.includedirs = ["include"]
        
        # System libraries for Linux
        self.cpp_info.system_libs = [
            "dl",
            "pthread",
            "rt",
            "X11",
            "Xext",
            "Xdamage",
            "Xfixes",
            "Xcomposite",
            "Xrandr",
        ]
        
        # Compiler flags
        if self.options.get_safe("fPIC"):
            self.cpp_info.cxxflags.append("-fPIC")
        
        # Defines
        self.cpp_info.defines = [
            "WEBRTC_POSIX",
            "WEBRTC_LINUX",
        ]
        
        if not self.options.shared:
            self.cpp_info.defines.append("WEBRTC_LIBRARY_IMPL")
        
        # Build type specific defines
        build_type = str(self.settings.build_type)
        if build_type == "Debug":
            self.cpp_info.defines.append("_DEBUG")
        else:
            self.cpp_info.defines.append("NDEBUG")