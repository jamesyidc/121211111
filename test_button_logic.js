// 测试按钮生成逻辑
const events = [
    {event_name: "强空头爆仓", action: "开空", event_id: 3},
    {event_name: "弱空头爆仓", action: "开空（谨慎）", event_id: 4}
];

events.forEach(event => {
    console.log(`\n测试事件: ${event.event_name}`);
    console.log(`Action: "${event.action}"`);
    
    if (event.action) {
        const action = event.action;
        let buttons = [];
        
        if (action.includes('开空')) {
            console.log("✅ 匹配到'开空'，应该生成3个按钮");
            buttons.push("空单策略 A");
            buttons.push("空单策略 B");
            buttons.push("多单配空单");
        }
        
        console.log(`生成按钮数量: ${buttons.length}`);
        console.log(`按钮列表: ${buttons.join(', ')}`);
    } else {
        console.log("❌ event.action为空");
    }
});
