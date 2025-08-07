import { sendApi } from "@main/lib.js";
import FormModel from "@main/Components/Form/FormModel";

class AgentPageModel
{
	constructor(layout)
	{
		this.layout = layout;
		this.items = [];
		this.llm = [];
		this.form = new FormModel();
	}
	
	
	/**
	 * Init
	 */
	init()
	{
	}
	
	
	/**
	 * Find item by id
	 */
	findItemById(id)
	{
		return this.items.find((item) => item.id == id);
	}
	
	
	/**
	 * Find LLM by id
	 */
	findLanguageModelById(id)
	{
		return this.llm.find((item) => item.id == id);
	}
	
	
	/**
	 * Load data
	 */
	async load()
	{
		this.items = [];
		var result = await sendApi(
			"/api/settings/agent",
		);
		if (result.isSuccess())
		{
			this.items = result.data.items;
		}
	}
	
	
	/**
	 * Load llm
	 */
	async loadLanguageModels()
	{
		this.llm = [];
		var result = await sendApi(
			"/api/settings/llm",
		);
		if (result.isSuccess())
		{
			this.llm = result.data.items;
		}
	}
	
		
	/**
	 * Save item
	 */
	async save(pk, item)
	{
		var result = await sendApi(
			"/api/settings/agent/save",
			{
				"id": pk ? pk.id : null,
				"item": item,
			}
		);
		return result;
	}
	
	
	/**
	 * Delete item
	 */
	async delete(id)
	{
		var result = await sendApi(
			"/api/settings/agent/delete",
			{
				"id": id,
			}
		);
		
		if (result.isSuccess())
		{
			var index = this.items.find((item) => item.id == id);
			this.items.slice(index, 1);
		}
		return result;
	}
}

export default AgentPageModel;