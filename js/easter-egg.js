// 小彩蛋：点击吃豆人进入游戏
(function() {
    function initEasterEgg() {
        // 查找吃豆人动画元素
        const avatarArea = document.querySelector('.avatar-img');
        
        if (!avatarArea) return;
        
        // 创建吃豆人小球
        const pacman = document.createElement('a');
        pacman.href = '/map/games/';
        pacman.title = '🎮 点击进入小游戏！';
        pacman.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 30px;
            height: 30px;
            background: linear-gradient(135deg, #feca57 0%, #ff9f43 100%);
            border-radius: 50%;
            cursor: pointer;
            z-index: 1000;
            animation: pacmanMove 3s ease-in-out infinite;
            box-shadow: 0 0 15px rgba(254, 202, 87, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none !important;
            transition: transform 0.3s, box-shadow 0.3s;
        `;
        
        // 添加嘴巴动画
        pacman.innerHTML = '<span style="font-size: 20px;">👾</span>';
        
        // 悬停效果
        pacman.onmouseenter = function() {
            this.style.transform = 'translate(-50%, -50%) scale(1.2)';
            this.style.boxShadow = '0 0 25px rgba(254, 202, 87, 1)';
        };
        
        pacman.onmouseleave = function() {
            this.style.transform = 'translate(-50%, -50%) scale(1)';
            this.style.boxShadow = '0 0 15px rgba(254, 202, 87, 0.8)';
        };
        
        // 点击事件
        pacman.onclick = function(e) {
            e.preventDefault();
            window.location.href = '/map/games/';
        };
        
        avatarArea.appendChild(pacman);
        
        // 添加提示
        const hint = document.createElement('div');
        hint.innerHTML = '🎮 点击这个小球进入小游戏！';
        hint.style.cssText = `
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 25px;
            border-radius: 25px;
            font-size: 14px;
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
            animation: bounce 2s infinite;
            z-index: 9999;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.5s;
        `;
        
        // 添加动画样式
        const style = document.createElement('style');
        style.textContent = `
            @keyframes bounce {
                0%, 100% { transform: translateX(-50%) translateY(0); }
                50% { transform: translateX(-50%) translateY(-8px); }
            }
            @keyframes pacmanMove {
                0%, 100% { left: 20%; }
                50% { left: 80%; }
            }
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(hint);
        
        // 淡入提示
        setTimeout(() => {
            hint.style.opacity = '1';
        }, 500);
        
        // 5秒后淡出提示
        setTimeout(() => {
            hint.style.opacity = '0';
            setTimeout(() => hint.remove(), 500);
        }, 5000);
        
        // 点击提示也进入游戏
        hint.onclick = function() {
            window.location.href = '/map/games/';
        };
    }
    
    // 页面加载后执行
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initEasterEgg);
    } else {
        initEasterEgg();
    }
})();
