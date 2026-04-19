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

const { init } = require("./init.js");
init();

const use = require("bay-lang").use;
const RuntimeMap = use("Runtime.Map");
const RuntimeVector = use("Runtime.Vector");
const Provider = use("Runtime.Entity.Provider");
const rtl = use("Runtime.rtl");

const static = {
	"assets":
	{
		"uri": "/assets",
		"path": __dirname + "/public/assets",
	},
	"vue":
	{
		"uri": "/assets/vue",
		"path": __dirname + "/node_modules/vue/dist",
	}
};

const params = new RuntimeMap({
	"providers": new RuntimeVector(
		new Provider("Runtime.AI.Providers.SentenceProvider"),
	),
	"modules": new RuntimeVector("App", "Runtime.Web"),
});

const app = new Provider("app", "Runtime.Web.Fastify", new RuntimeMap({ static, port: 80 }));
rtl.runApp(app, params);