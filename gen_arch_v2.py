from graphviz import Digraph
import os

def draw_architecture():
    # 1. 基础设置：增加默认字体大小，让节点看起来更饱满
    dot = Digraph(comment='RapidRAR Architecture', format='svg')
    # rankdir='LR' 依然是左到右，但我们通过 grouping 技巧来折行
    dot.attr(rankdir='LR', compound='true', splines='ortho', nodesep='0.6', ranksep='0.8')
    
    dot.attr('node', shape='rect', style='filled', 
             fontname='Helvetica', fontsize='14', margin='0.25') # 字体加大
    dot.attr('edge', fontname='Helvetica', fontsize='11')
    
    # 配色
    colors = {
        'host_bg': '#F5F7FA',
        'device_bg': '#E8F5E9',
        'node_host': '#FFFFFF',
        'node_device': '#FFFFFF',
        'stroke': '#333333',
        'accent': '#2E7D32',
        'validation_bg': '#FFF3E0' # 给验证层加个淡淡的橙色背景区分
    }

    # Start 节点
    dot.node('start', 'Start / CLI', shape='circle', width='1.0', style='filled', fillcolor='#333333', fontcolor='white')

    # --- 第一行：Host -> Device ---

    # Host Context
    with dot.subgraph(name='cluster_0') as c:
        c.attr(style='filled', color=colors['host_bg'], label='🐍 Host Context (Control Plane)', fontcolor='#555555', fontsize='16')
        c.node('init', 'GPU Manager\n(RAII Context)', fillcolor=colors['node_host'], color=colors['stroke'])
        c.node('batcher', 'Batch Generator\n(Dynamic Batching)', fillcolor=colors['node_host'], color=colors['stroke'])
        c.node('pool', 'ThreadPool\n(Task Dispatch)', fillcolor=colors['node_host'], color=colors['stroke'])
        
        c.edge('init', 'batcher', style='invis') # 隐形线辅助布局
        c.edge('batcher', 'pool', label='Tasks')

    # Device Context
    with dot.subgraph(name='cluster_1') as c:
        c.attr(style='filled', color=colors['device_bg'], label='⚡ Device Context (Data Plane)', fontcolor='#2E7D32', fontsize='16')
        c.node('vram_in', 'Pinned Memory\n(Input Buffer)', shape='cylinder', fillcolor=colors['node_device'], color=colors['accent'])
        c.node('kernel', 'CUDA Kernel\n(Parallel Hash)', shape='component', fillcolor=colors['node_device'], color=colors['accent'])
        c.node('vram_out', 'Result Bitmap\n(Output Buffer)', shape='cylinder', fillcolor=colors['node_device'], color=colors['accent'])
        
        c.edge('vram_in', 'kernel')
        c.edge('kernel', 'vram_out')

    # --- 第二行：Validation (通过 invisible edge 强制换行) ---
    
    with dot.subgraph(name='cluster_2') as c:
        c.attr(style='dashed', color='#FFB74D', label='🛡️ Validation Layer', fontcolor='#F57C00', fontsize='16')
        
        # 为了让它排在下面，我们可以不用 rankdir，而是依赖连线逻辑
        # 但最简单的方法是把这层独立出来
        c.node('filter', 'Candidate?', shape='diamond', style='filled', fillcolor='#FFFFFF', color='#F57C00')
        c.node('check', 'UnRAR Verify\n(CPU Check)', fillcolor='#FFFFFF', color='#F57C00')
        c.node('success', 'Success\nPassword Found', shape='doublecircle', fillcolor=colors['accent'], fontcolor='white')

        c.edge('filter', 'check', label=' Yes')
        c.edge('check', 'success', label=' Pass')

    # --- 关键连线 ---
    
    # 1. Start -> Host
    dot.edge('start', 'init')
    
    # 2. Host -> Device (PCIe H2D)
    dot.edge('pool', 'vram_in', label=' PCIe Bus (H2D)', penwidth='3.0', color='#333333')

    # 3. Device -> Validation (PCIe D2H) - 关键：这会让图折行
    # 我们不直接连，而是用 constraint=false 来允许它“掉”下来，或者利用 Graphviz 的自然布局
    # 这里的技巧是：Device 在上，Validation 在下
    
    dot.edge('vram_out', 'filter', label=' PCIe Bus (D2H)', penwidth='3.0', color='#333333')
    
    # 4. 回环 (Validation -> Host)
    # False Positive 回到 Batcher
    dot.edge('check', 'batcher', label=' False Positive\n(Retry)', style='dotted', color='#d32f2f', fontcolor='#d32f2f', constraint='false')
    # No Candidate 回到 Batcher
    dot.edge('filter', 'batcher', label=' No', style='dotted', constraint='false')

    output_path = 'assets/architecture_v2'
    # Ensure assets directory exists
    os.makedirs('assets', exist_ok=True)
    dot.render(output_path, view=False)
    print(f"✅ Generated: {output_path}.svg (More compact version)")

if __name__ == '__main__':
    draw_architecture()
