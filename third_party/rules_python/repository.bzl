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

def load_repository():
    if native.existing_rule("rules_python"):
        return

    rules_python_version = "0efcd94d0ee6e1e56b27d25469c28502282fab5b"

    _http_archive(
        name = "rules_python",
        sha256 = "e611111d092e54f04e0818d1bc89aad6a841c6f50cbe96e8ec13a6eddcfbf354",
        strip_prefix = "rules_python-{}".format(rules_python_version),
        url = "https://github.com/bazelbuild/rules_python/archive/{}.zip".format(rules_python_version),
    )
