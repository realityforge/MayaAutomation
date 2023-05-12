# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

load("@bazel_tools//tools/build_defs/repo:http.bzl", _http_archive = "http_archive")

_VERSIONS = {
    "2023_3": {
        "windows": {
            "url": "https://autodesk-adn-transfer.s3-us-west-2.amazonaws.com/ADN+Extranet/M%26E/Maya/devkit+2023/Autodesk_Maya_2023_3_Update_DEVKIT_Windows.zip",
            "sha256": "fda98a87e2897a93d64843cf1a5024eb4bcd55968c80ff3af69142e3d5d0c23f",
            "prefix": "devkitBase",
        },
    },
}

def load_repository():
    if native.existing_rule("maya_devkit"):
        return

    # TODO: Logic should be here to get the version and the OS. We can add it when we need it.
    version = "2023_3"
    variant = "windows"
    url = _VERSIONS[version][variant]["url"]
    sha256 = _VERSIONS[version][variant]["sha256"]
    prefix = _VERSIONS[version][variant]["prefix"]

    _http_archive(name = "maya_devkit", sha256 = sha256, strip_prefix = prefix, url = url, build_file = "@//third_party/maya_devkit:maya_devkit.BUILD.bazel")
