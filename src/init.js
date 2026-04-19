/*!
 *  BayLang AI
 *
 *  (c) Copyright 2026 "Ildar Bikmamatov" <support@bayrell.org>
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      https://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

const use = require("bay-lang").use;

function include(path)
{
	use.include(__dirname + path);
}

exports.init = function()
{
	/* Framework */
	include("/lib/Runtime/nodejs/index.js");
	include("/lib/Runtime.Console/nodejs/index.js");
	include("/lib/Runtime.ORM/nodejs/index.js");
	include("/lib/Runtime.Unit/nodejs/index.js");
	include("/lib/Runtime.Web/nodejs/index.js");
	include("/lib/Runtime.Widget/nodejs/index.js");

	/* App */
	include("/lib/Runtime.AI/nodejs/index.js");
	include("/lib/Runtime.Auth/nodejs/index.js");
	include("/lib/Runtime.Cabinet/nodejs/index.js");
	include("/lib/Runtime.Crypt/nodejs/index.js");
	include("/lib/App/nodejs/index.js");
	
	if (process.env["DEBUG"] == "true")
	{
		process.env["DEBUG"] = true;
	}
	if (process.env["TZ"] == undefined)
	{
		process.env["TZ"] = "Asia/Almaty";
	}
	process.env["TZ_OFFSET"] = -60*(new Date().getTimezoneOffset());
}