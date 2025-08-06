import ResultModel from "../Form/ResultModel.js";

class DialogModel
{
	is_show = false;
	data = null;
	result = new ResultModel();
	
	show()
	{
		this.is_show = true;
	}
	
	hide()
	{
		this.is_show = false;
	}
	
	
	/**
	 * Set api result
	 */
	setApiResult(api_result)
	{
		this.result.setApiResult(api_result);
	}
	
	setData(data)
	{
		this.data = Object.assign({}, data);
	}
}

export default DialogModel;