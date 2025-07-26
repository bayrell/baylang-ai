class ChatMessage
{
	id = "";
	sender = "";
	content = [];
	
	
	/**
	 * Assign
	 */
	assign(data)
	{
		this.id = data.id;
		this.sender = data.sender;
		this.content = data.content;
	}
	
	
	/**
	 * Returns lines
	 */
	getLines()
	{
		if (Array.isArray(this.content)) return this.content;
		return [];
	}
	
	
	/**
	 * Last line
	 */
	lastLine()
	{
		var lines = this.getLines();
		if (lines.length == 0) return null;
		return lines[lines.length - 1];
	}
}

export default ChatMessage;