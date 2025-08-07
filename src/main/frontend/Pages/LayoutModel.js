import AgentPageModel from "./Agent/AgentPageModel.js";
import ChatPageModel from "./Chat/ChatPageModel.js";
import LLM from "./LLM/LLM.js";
import Router from "./Router.js";

class Layout
{
	constructor()
	{
		this.router = new Router(this);
		this.agent_page = new AgentPageModel(this);
		this.chat_page = new ChatPageModel(this);
		this.llm_page = new LLM(this);
	}
	
	
	/**
	 * Init layout
	 */
	init()
	{
		this.router.init();
		this.agent_page.init();
		this.chat_page.init();
		this.llm_page.init();
	}
	
	
	/**
	 * Load data
	 */
	async load()
	{
	}
	
	
	/**
	 * Repaint
	 */
	repaint()
	{
	}
}

export default Layout;