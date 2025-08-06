class ResultModel
{
    constructor()
    {
        this.code = 0;
        this.message = "";
        this.result = null;
    }
    
    
    /**
     * Clear
     */
    clear()
    {
        this.code = 0;
        this.message = "";
    }
    
    
    /**
     * Set api result
     */
    setApiResult(result)
    {
        this.result = result;
        this.code = result.code;
        this.message = result.message;
    }
    
    
    /**
     * Set wait message
     */
    setWaitMessage()
    {
        this.message = "Wait please ...";
    }
}

export default ResultModel;