<script>
// 头像区域吃豆人小球点击彩蛋
document.addEventListener('DOMContentLoaded', function() {
    // 查找吃豆人动画元素
    const avatarImg = document.querySelector('.avatar-img img');
    const avatarContainer = document.querySelector('.avatar-img');
    
    if (avatarContainer) {
        // 创建可点击的吃豆人小球
        const pacman = document.createElement('div');
        pacman.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 20px;
            height: 20px;
            background: #feca57;
            border-radius: 50%;
            cursor: pointer;
            z-index: 100;
            animation: pacmanEat 2s infinite linear;
            box-shadow: 0 0 10px #feca57;
        `;
        
        // 添加吃豆人嘴巴动画
        const style = document.createElement('style');
        style.textContent = `
            @keyframes pacmanEat {
                0% { clip-path: polygon(50% 50%, 100% 0, 100% 100%, 50% 50%, 100% 100%, 100% 0); }
                25% { clip-path: polygon(50% 50%, 100% 0, 100% 100%, 50% 50%, 100% 100%, 100% 0); transform: translate(-50%, -50%) rotate(0deg); }
                50% { clip-path: polygon(50% 50%, 100% 0, 100% 100%, 50% 50%, 100% 100%, 100% 0); transform: translate(-50%, -50%) rotate(180deg); }
                75% { clip-path: polygon(50% 50%, 100% 0, 100% 100%, 50% 50%, 100% 100%, 100% 0); transform: translate(-50%, -50%) rotate(180deg); }
                100% { clip-path: polygon(50% 50%, 100% 0, 100% 100%, 50% 50%, 100% 100%, 100% 0); transform: translate(-50%, -50%) rotate(360deg); }
            }
            .pacman-hint {
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px 30px;
                border-radius: 30px;
                font-size: 16px;
                box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
                animation: bounce 2s infinite;
                z-index: 9999;
                cursor: pointer;
            }
            @keyframes bounce {
                0%, 100% { transform: translateX(-50%) translateY(0); }
                50% { transform: translateX(-50%) translateY(-10px); }
            }
        `;
        document.head.appendChild(style);
        
        // 点击事件
        pacman.onclick = function() {
            window.location.href = '/map/games/';
        };
        
        avatarContainer.appendChild(pacman);
        
        // 显示提示
        const hint = document.createElement('div');
        hint.className = 'pacman-hint';
        hint.innerHTML = '🎮 点击吃豆人进入小游戏！';
        hint.onclick = function() {
            window.location.href = '/map/games/';
            hint.remove();
        };
        document.body.appendChild(hint);
        
        // 5秒后隐藏提示
        setTimeout(() => {
            hint.style.opacity = '0';
            hint.style.transition = 'opacity 1s';
            setTimeout(() => hint.remove(), 1000);
        }, 5000);
    }
});
</script>
