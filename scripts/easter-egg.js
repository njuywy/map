// scripts/easter-egg.js
// 彩蛋：连续点击头像3次进入游戏页面

hexo.extend.filter.register('after_render:html', function(html, data) {
    const easterEggScript = `
<!-- 彩蛋脚本：连续点击头像3次进入游戏页面 -->
<style>
.avatar-click-counter {
    position: fixed !important;
    top: 20px !important;
    right: 20px !important;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    padding: 15px 25px !important;
    border-radius: 15px !important;
    font-size: 16px !important;
    box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4) !important;
    z-index: 9999 !important;
    opacity: 0 !important;
    transition: opacity 0.3s !important;
    cursor: pointer !important;
}
.avatar-click-counter.show {
    opacity: 1 !important;
    animation: pulse 0.5s ease-in-out;
}
@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); }
}
.easter-egg-success {
    position: fixed !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    background: linear-gradient(135deg, #00b894 0%, #00cec9 100%) !important;
    color: white !important;
    padding: 30px 50px !important;
    border-radius: 20px !important;
    font-size: 24px !important;
    font-weight: bold !important;
    box-shadow: 0 10px 40px rgba(0, 184, 148, 0.5) !important;
    z-index: 10000 !important;
    text-align: center !important;
    animation: bounceIn 0.5s ease-out !important;
}
@keyframes bounceIn {
    0% { transform: translate(-50%, -50%) scale(0); }
    50% { transform: translate(-50%, -50%) scale(1.1); }
    100% { transform: translate(-50%, -50%) scale(1); }
}
</style>
<script>
(function(){
    var clickCount = 0;
    var clickTimer = null;
    var avatarArea = document.querySelector('.avatar-img') || document.querySelector('#aside-profile') || document.querySelector('.author-info');
    var counter = null;
    var successShown = false;
    
    if (!avatarArea) return;
    
    avatarArea.style.cursor = 'pointer';
    avatarArea.title = '🎮 连续点击3次进入游戏页面！';
    
    avatarArea.addEventListener('click', function(e){
        if (successShown) return;
        
        clickCount++;
        
        // 显示计数器
        if (!counter) {
            counter = document.createElement('div');
            counter.className = 'avatar-click-counter';
            counter.innerHTML = '🎮 已点击 <span id="clickNum">0</span>/3 次';
            document.body.appendChild(counter);
        }
        
        document.getElementById('clickNum').textContent = clickCount;
        counter.classList.add('show');
        
        // 视觉反馈
        avatarArea.style.transition = 'transform 0.1s';
        avatarArea.style.transform = 'scale(0.95)';
        setTimeout(function(){
            avatarArea.style.transform = 'scale(1)';
        }, 100);
        
        // 清除之前的定时器
        if (clickTimer) clearTimeout(clickTimer);
        
        // 检查是否达到3次
        if (clickCount >= 3) {
            successShown = true;
            
            // 显示成功提示
            var success = document.createElement('div');
            success.className = 'easter-egg-success';
            success.innerHTML = '🎉 恭喜触发彩蛋！<br><br>正在进入游戏页面...';
            document.body.appendChild(success);
            
            // 3秒后跳转
            setTimeout(function(){
                window.location.href = '/map/games/';
            }, 1500);
            
            // 移除计数器
            if (counter) {
                counter.classList.remove('show');
                setTimeout(function(){ counter.remove(); }, 300);
            }
        } else {
            // 重置计时器
            clickTimer = setTimeout(function(){
                clickCount = 0;
                if (counter) {
                    counter.classList.remove('show');
                    document.getElementById('clickNum').textContent = '0';
                }
            }, 3000);
        }
    });
    
    // 本地存储状态
    try {
        var savedState = localStorage.getItem('avatarEasterEgg');
        if (savedState === 'triggered') {
            // 已经触发过，显示简短提示
            var hint = document.createElement('div');
            hint.className = 'avatar-click-counter show';
            hint.innerHTML = '🎮 <a href="/map/games/" style="color:white;text-decoration:underline;">点击这里进入游戏页面</a>';
            document.body.appendChild(hint);
        }
    } catch(e) {}
})();
</script>
`;
    
    return html.replace('</body>', easterEggScript + '</body>');
});
