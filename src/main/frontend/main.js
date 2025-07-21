import { createApp, reactive } from "vue"
import Layout from "./Pages/Layout.vue";
import LayoutModel from "./Pages/LayoutModel.js";
import "./main.scss";

/* Register layout */
const registerLayout = (layout) => {
	return {
		install: (app) => {
			app.config.globalProperties.layout = layout;
		},
	};
};

/* Start app */
window.startApp = (callback) => {
	
	/* Create layout */
	let layout = reactive(new LayoutModel());
	window.app_layout = layout;

	/* Init layout */
	layout.init();
	
	/* Create app */
	const app = createApp(Layout);
	app.use(registerLayout(layout));
	
	if (callback)
	{
		callback(app, layout);
	}
}