import hashlib
import json
import time
import os
import random
from tkinter import *
from tkinter import messagebox, scrolledtext, ttk
from collections import OrderedDict
import easygui
import ctypes
import webbrowser




# --- 常量定义 ---
MINING_DIFFICULTY = 0  # 增加难度到 0
MINING_REWARD = 5      # 增加奖励
GENESIS_PREV_HASH = "0" * 64
BLOCKCHAIN_FILENAME = "improved_tcoin_chain.json"






# --- 辅助类：钱包/用户账户模拟 ---
class Wallet:
    """模拟一个用户的钱包，包含地址（公钥）和私钥。"""
    
    @staticmethod
    def generate_key_pair():
        """模拟生成一个公钥和私钥。"""
        # 实际的区块链会使用 ECC 算法。这里简化为随机哈希。
        private_key = hashlib.sha256(str(time.time() + random.random()).encode()).hexdigest()
        # 公钥（地址）可以从私钥派生，这里直接简化为另一个哈希
        public_key = hashlib.sha256(private_key.encode()).hexdigest()[:40] # 截断作为地址
        return public_key, private_key

    @staticmethod
    def sign_transaction(private_key, transaction_data):
        """使用私钥对交易数据进行签名。"""
        # 简化签名过程：将交易数据和私钥哈希
        tx_string = json.dumps(transaction_data, sort_keys=True)
        signature = hashlib.sha256((tx_string + private_key).encode()).hexdigest()
        return signature

    @staticmethod
    def verify_signature(public_key, signature, transaction_data):
        """验证签名是否有效。"""
        # 真正的验证需要复杂的加密算法。这里简化为：
        if transaction_data.get('sender') == "SYSTEM":
            return True
            
        return len(signature) == 64 and public_key is not None

# --- 区块链核心逻辑 ---

class Blockchain:
    def __init__(self):
        self.pending_transactions = []  # 待处理的交易
        self.chain = []                 # 完整的区块链
        #------------网络节点（为未来P2P扩展预留）---------------
        self.nodes = set()

        self.wallets = {"My_Wallet": "mock_private_key_001"} # 存储用户的私钥 (不安全，仅为模拟)

        # 尝试从文件加载
        if not self.load_chain(BLOCKCHAIN_FILENAME):
            
            
            easygui.msgbox("""未找到本地区块链文件，已为您创建区块链文件
点击确定进入T币挖掘模拟器""", title="提示")
            
            #print("未找到本地区块链文件，正在创建创世区块...")
            # 创建创世区块
            self.mine_block(proof=100, previous_hash=GENESIS_PREV_HASH, transactions=[], miner_address="SYSTEM")

    @property
    def last_block(self):
        """返回链上的最后一个区块"""
        return self.chain[-1]

    @staticmethod
    def hash_block(block):
        """对一个区块进行 SHA-256 哈希计算。使用 OrderedDict 保证一致性。"""
        block_string = json.dumps(OrderedDict(block), sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def register_new_wallet(self, user_alias):
        """注册一个新用户，并生成钱包。"""
        public_key, private_key = Wallet.generate_key_pair()
        self.wallets[user_alias] = private_key
        return public_key

    def new_transaction(self, sender, recipient, amount, sender_private_key=None):
        """
        创建一个新交易，并将其添加到待处理交易列表中
        """
        try:
            amount = float(amount)
        except ValueError:
            easygui.msgbox("交易失败：金额必须是数字。", title="警告")
            print("交易失败：金额必须是数字。")
            return False

        if not isinstance(amount, (int, float)) or amount <= 0:
            easygui.msgbox(f"交易失败：金额 {amount} 必须是正数。", title="警告")
            print(f"交易失败：金额 {amount} 必须是正数。")
            return False
        
        # 1. 检查余额 (除了 SYSTEM 账户)
        if sender != "SYSTEM":
            if self.get_balance(sender) < amount:
                easygui.msgbox(f"交易失败： {sender} 余额不足。")
                print(f"交易失败： {sender} 余额不足。")
                return False
            
            # 2. 模拟签名
            if sender_private_key is None:
                print("交易失败：用户交易需要私钥进行签名。")
                return False

        transaction_data = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'timestamp': time.time(),
        }
        
        # 3. 生成签名
        signature = Wallet.sign_transaction(sender_private_key or "", transaction_data)
        
        transaction = {**transaction_data, 'signature': signature}
        
        self.pending_transactions.append(transaction)
        print(f"交易已添加：{sender} -> {recipient} ({amount} T币)")
        return True

    def mine_block(self, proof, previous_hash, transactions, miner_address):
        """
        创建并添加一个新区块到链上
        """
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'transactions': transactions,
            'proof': proof,
            'previous_hash': previous_hash,
            'miner': miner_address,
        }
        
        # 计算并添加当前区块的哈希值
        block['hash'] = self.hash_block(block)
        
        # 将新区块添加到链上
        self.chain.append(block)
        return block

    def perform_proof_of_work(self, last_proof, transactions, difficulty):
        """
        工作量证明：
        - 找到一个 'proof' (nonce)，使得它与 'last_proof' 和 'transactions' 的哈希值
          结合后，其哈希值以 'difficulty' 个 '0' 开头。
        """
        proof = 0
        while not self.is_valid_proof(last_proof, proof, transactions, difficulty):
            proof += 1
        return proof

    @staticmethod
    def is_valid_proof(last_proof, proof, transactions, difficulty):
        """
        验证证明是否有效：哈希值是否满足难度要求？
        """
        transactions_string = json.dumps(transactions, sort_keys=True).encode()
        guess = f'{last_proof}{proof}{transactions_string}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:difficulty] == '0' * difficulty
        
    def get_difficulty(self):
        """模拟难度调整：每 10 个区块难度加 1，最多不超过 8"""
        base_difficulty = MINING_DIFFICULTY
        adjust = len(self.chain) // 10
        return min(base_difficulty + adjust, 8)

    def get_balance(self, user):
        """
        计算并返回指定用户的余额
        """
        balance = 0
        for block in self.chain:
            for tx in block['transactions']:
                if tx['sender'] == user:
                    balance -= tx['amount']
                if tx['recipient'] == user:
                    balance += tx['amount']
        return balance

    def get_all_balances(self):
        """获取所有参与过的用户的余额"""
        balances = {}
        for block in self.chain:
            for tx in block['transactions']:
                balances[tx['sender']] = balances.get(tx['sender'], 0) - tx['amount']
                balances[tx['recipient']] = balances.get(tx['recipient'], 0) + tx['amount']
        
        if "SYSTEM" in balances:
            del balances["SYSTEM"]
            
        return balances

    def is_chain_valid(self):
        """检查整个区块链是否有效（防篡改），包含工作量证明的重新验证"""
        for i in range(1, len(self.chain)):
            
            current_block = self.chain[i]
            prev_block = self.chain[i-1]
            if i > 1:
                # 1. 检查前一个哈希是否匹配
                if current_block['previous_hash'] != self.hash_block(prev_block):
                    print(f"链条断裂：区块 {i} 的 previous_hash 与 区块 {i-1} 的哈希不符。")
                    return False
                    
                # 2. 检查工作量证明是否仍然有效
                last_proof = prev_block['proof']
                transactions_to_verify = current_block['transactions']
                current_difficulty = self.get_difficulty() 
                
                if not self.is_valid_proof(last_proof, current_block['proof'], transactions_to_verify, current_difficulty):
                    print(f"区块 {i} 的工作量证明无效（Nonce={current_block['proof']}，难度={current_difficulty}）。")
                    return False
                    
                # 3. 检查区块自带的哈希是否正确
                if current_block['hash'] != self.hash_block(current_block):
                    print(f"区块 {i} 的哈希值不正确。")
                    return False
                
                # 所有检查通过，返回True（新增这一行）
                return True
            else:
                # i <= 1 时直接返回True（通常是创世区块）
                return True

        easygui.msgbox("""区块链验证通过
点击确定继续使用T币挖掘模拟器""", title="提示")
        print("区块链验证通过。")
        return True

    def save_chain(self, filename):
        """将区块链和待处理交易保存到文件"""
        try:
            data = {
                'chain': self.chain,
                'pending_transactions': self.pending_transactions,
                'wallets': self.wallets
            }
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"保存失败: {e}")
            return False

    def load_chain(self, filename):
        """从文件加载区块链和待处理交易"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                self.chain = data['chain']
                self.pending_transactions = data.get('pending_transactions', [])
                self.wallets = data.get('wallets', {"My_Wallet": "mock_private_key_001"})
            
            if not self.is_chain_valid():
                print("警告：加载的区块链验证失败！")
                
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"加载失败: {e}")
            return False


# --- GUI 界面部分 (使用 ttk 增强) ---

class BlockchainApp:
    def __init__(self, root, blockchain):
        self.blockchain = blockchain
        self.root = root
        self.root.title("Tcoin 挖掘模拟器 v0.1.1")  # 窗口标题
        self.root.geometry("1440x920")  # 固定窗口大小
        
        # 禁止窗口缩放
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except:
            ctypes.windll.user32.SetProcessDPIAware()
        

        # --- 状态变量 ---
        self.is_mining_continous = False
        self.mining_interval_ms = 100 # 持续挖矿时，每次循环检查的间隔（毫秒）

        # 矿工身份（使用默认钱包）
        self.miner_id = "My_Wallet"
        if self.miner_id not in self.blockchain.wallets:
             self.blockchain.register_new_wallet(self.miner_id)

        # 样式设置
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0')
        style.configure('TButton', padding=6, font=('Arial', 10, 'bold'))
        style.map('TButton', foreground=[('active', 'blue'), ('pressed', 'red')])
        
        # --- 主容器 ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=BOTH, expand=True)

        # --- 控制区 (左侧) ---
        control_frame = ttk.Frame(main_frame, padding="5", relief=GROOVE)
        control_frame.pack(side=LEFT, fill=Y, padx=10)
        
        # 钱包信息
        wallet_frame = ttk.LabelFrame(control_frame, text=f"当前矿工/发送方 ({self.miner_id})", padding="10")
        wallet_frame.pack(pady=10, fill=X)
        ttk.Label(wallet_frame, text="身份/钱包名:", font=('Arial', 10, 'bold')).pack(side=LEFT, padx=5)
        self.miner_id_var = StringVar(value=self.miner_id)
        self.miner_id_entry = ttk.Entry(wallet_frame, textvariable=self.miner_id_var, width=15)
        self.miner_id_entry.pack(side=LEFT, fill=X, expand=True, padx=5)
        self.set_miner_button = ttk.Button(wallet_frame, text="切换/创建钱包", command=self.set_miner, width=15)
        self.set_miner_button.pack(side=LEFT)


        # 转账交易
        tx_frame = ttk.LabelFrame(control_frame, text="创建交易 (需私钥签名)", padding="10")
        tx_frame.pack(pady=10, fill=X)
        
        ttk.Label(tx_frame, text="接收方:", width=10).grid(row=0, column=0, sticky=W, pady=2)
        self.recipient_entry = ttk.Entry(tx_frame)
        self.recipient_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.recipient_entry.insert(0, "Bob")

        ttk.Label(tx_frame, text="金额:", width=10).grid(row=1, column=0, sticky=W, pady=2)
        self.amount_entry = ttk.Entry(tx_frame)
        self.amount_entry.grid(row=1, column=1, sticky="ew", padx=5)
        self.amount_entry.insert(0, "10.0")

        self.tx_button = ttk.Button(tx_frame, text="提交交易 (签名)", command=self.create_transaction)
        self.tx_button.grid(row=2, columnspan=2, pady=10, sticky="ew")
        
        tx_frame.grid_columnconfigure(1, weight=1)

        # 挖矿和存取
        action_frame = ttk.LabelFrame(control_frame, text="核心操作", padding="10")
        action_frame.pack(pady=10, fill=X)
        
        # --- 持续挖矿控制 (新增) ---
        ttk.Label(action_frame, text="挖矿模式:", font=('Arial', 10, 'bold')).pack(pady=(5, 0))
        
        self.mine_button = ttk.Button(action_frame, text="⛏ 单次挖矿 (PoW)", command=self.mine_block_single)
        self.mine_button.pack(pady=5, fill=X)
        
        self.start_cont_mine_button = ttk.Button(action_frame, text="🚀 开始持续挖矿", command=self.start_continuous_mining)
        self.start_cont_mine_button.pack(pady=5, fill=X)
        
        self.stop_cont_mine_button = ttk.Button(action_frame, text="🛑 停止持续挖矿", command=self.stop_continuous_mining, state=DISABLED)
        self.stop_cont_mine_button.pack(pady=5, fill=X)
        
        ttk.Separator(action_frame, orient=HORIZONTAL).pack(fill=X, pady=10)

        # 存取和验证
        self.save_button = ttk.Button(action_frame, text="保存区块链 (.json)", command=self.save_data)
        self.save_button.pack(pady=5, fill=X)
        
        self.load_button = ttk.Button(action_frame, text="加载区块链 (.json)", command=self.load_data)
        self.load_button.pack(pady=5, fill=X)
        
        self.validate_button = ttk.Button(action_frame, text="验证区块链完整性", command=self.validate_chain)
        self.validate_button.pack(pady=5, fill=X)

        self.about_us = ttk.Button(action_frame, text="关于我们", command=self.about_us)
        self.about_us.pack(pady=5, fill=X)
        

        # 难度显示
        self.difficulty_label = ttk.Label(action_frame, text=f"当前挖矿难度: {self.blockchain.get_difficulty()} ('0'开头)")
        self.difficulty_label.pack(pady=(10,0))
        ttk.Label(action_frame, text=f"矿工奖励: {MINING_REWARD} T币").pack(pady=(0,5))


        # --- 显示区 (右侧 - 使用 Notebook 实现 Tab) ---
        display_container = ttk.Frame(main_frame, padding="5")
        display_container.pack(side=RIGHT, fill=BOTH, expand=True)
        
        self.notebook = ttk.Notebook(display_container)
        self.notebook.pack(fill=BOTH, expand=True, pady=5)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # 1. 区块链 Tab
        chain_tab = ttk.Frame(self.notebook)
        self.notebook.add(chain_tab, text='完整区块链')
        self.chain_text = scrolledtext.ScrolledText(chain_tab, wrap=WORD, state=DISABLED, font=('Consolas', 9), background='#2e2e2e', foreground='#f0f0f0', insertbackground='#f0f0f0')
        self.chain_text.pack(fill=BOTH, expand=True)

        # 2. 余额 Tab
        balance_tab = ttk.Frame(self.notebook)
        self.notebook.add(balance_tab, text='账户余额')
        self.balance_text = scrolledtext.ScrolledText(balance_tab, wrap=WORD, state=DISABLED, font=('Consolas', 10), background='#000', foreground='#f0f0f0', insertbackground='#f0f0f0')
        self.balance_text.pack(fill=BOTH, expand=True)

        # 3. 待处理 Tab
        pending_tab = ttk.Frame(self.notebook)
        self.notebook.add(pending_tab, text='待处理交易')
        self.pending_text = scrolledtext.ScrolledText(pending_tab, wrap=WORD, state=DISABLED, font=('Consolas', 10),background='#2e2e2e', foreground='#f0f0f0', insertbackground='#f0f0f0')
        self.pending_text.pack(fill=BOTH, expand=True)
        
        # --- 状态栏 ---
        self.status_bar = ttk.Label(self.root, text="就绪。", relief=SUNKEN, anchor=W)
        self.status_bar.pack(side=BOTTOM, fill=X)
        
        # 初始显示
        self.update_display()

    def set_miner(self):
        """切换当前操作的矿工/发送方钱包"""
        new_miner_id = self.miner_id_var.get().strip()
        if not new_miner_id:
            messagebox.showerror("错误", "钱包名不能为空。")
            self.miner_id_var.set(self.miner_id) # 恢复原值
            return

        if new_miner_id not in self.blockchain.wallets:
            # 创建新钱包
            address = self.blockchain.register_new_wallet(new_miner_id)
            messagebox.showinfo("钱包创建成功", f"新钱包 '{new_miner_id}' 已创建！\n地址: {address}\n(私钥已存储，仅用于本模拟)")
        
        self.miner_id = new_miner_id
        self.update_status_bar(f"已切换到钱包: {self.miner_id} | 余额: {self.blockchain.get_balance(self.miner_id):.2f} T币")
        self.update_display()

    def update_status_bar(self, message):
        """更新状态栏信息"""
        self.status_bar.config(text=message)
        
    def create_transaction(self):
        sender = self.miner_id
        recipient = self.recipient_entry.get().strip()
        try:
            amount = float(self.amount_entry.get())
        except ValueError:
            messagebox.showerror("错误", "金额必须是数字。")
            return

        if not sender or not recipient:
            messagebox.showerror("错误", "发送方和接收方不能为空。")
            return
            
        # 获取私钥（模拟）
        sender_private_key = self.blockchain.wallets.get(sender)
        if not sender_private_key:
             messagebox.showerror("错误", f"找不到钱包 '{sender}' 的私钥，无法签名。")
             return

        if self.blockchain.new_transaction(sender, recipient, amount, sender_private_key):
            messagebox.showinfo("成功", "交易已添加到待处理列表。")
            self.recipient_entry.delete(0, END)
            self.amount_entry.delete(0, END)
            self.amount_entry.insert(0, "10.0")
            
            self.notebook.select(self.notebook.tabs()[2]) # 切换到待处理交易视图
            self.update_display()
        else:
             # new_transaction 内部会打印具体失败原因
             pass 
             
    def mine_block_logic(self):
        """核心挖矿逻辑，供单次和持续挖矿调用"""
        
        # 1. 获取上一个区块的数据
        last_block = self.blockchain.last_block
        last_proof = last_block['proof']
        
        # 2. 从待处理交易中复制列表
        transactions_to_mine = list(self.blockchain.pending_transactions)

        # 3. 添加"挖矿奖励"交易
        reward_tx_data = {
            'sender': "SYSTEM",
            'recipient': self.miner_id,
            'amount': MINING_REWARD,
            'timestamp': time.time(),
        }
        # 简化签名
        reward_signature = Wallet.sign_transaction("SYSTEM_PRIVATE_KEY", reward_tx_data)
        transactions_to_mine.insert(0, {**reward_tx_data, 'signature': reward_signature})

        # 4. 获取当前难度
        current_difficulty = self.blockchain.get_difficulty()

        # 5. 执行工作量证明
        start_time = time.time()
        proof = self.blockchain.perform_proof_of_work(last_proof, transactions_to_mine, current_difficulty)
        elapsed = time.time() - start_time

        # 6. 清空待处理交易列表
        self.blockchain.pending_transactions = []
        
        # 7. 创建新区块并添加到链上
        block = self.blockchain.mine_block(proof, last_block['hash'], transactions_to_mine, self.miner_id)
        
        return block, elapsed

    def mine_block_single(self):
        """单次挖矿按钮的响应函数"""
        self.mine_button.config(text="🔥 正在挖矿...", state=DISABLED)
        self.root.update_idletasks() # 强制更新UI

        self.update_status_bar(f"开始单次挖矿... 当前难度: {self.blockchain.get_difficulty()}")
        
        try:
            block, elapsed = self.mine_block_logic()
            
            self.update_status_bar(f"单次挖矿成功！用时: {elapsed:.2f}s | 区块 #{block['index']}")
            messagebox.showinfo("挖矿成功", f"新区块 #{block['index']} 已被挖出！\n用时: {elapsed:.2f}s\n获得 {MINING_REWARD} T币奖励。")
            
            self.notebook.select(self.notebook.tabs()[0])
            self.update_display()
            
        except Exception as e:
            messagebox.showerror("挖矿失败", f"挖矿过程中发生错误: {e}")
        finally:
            self.mine_button.config(text="单次挖矿 (PoW)", state=NORMAL)


    # --- 持续挖矿功能 ---

    def start_continuous_mining(self):
        """启动持续挖矿模式"""
        if self.is_mining_continous:
            return
            
        self.is_mining_continous = True
        self.start_cont_mine_button.config(state=DISABLED)
        self.stop_cont_mine_button.config(state=NORMAL)
        self.mine_button.config(state=DISABLED) # 禁用单次挖矿
        
        self.update_status_bar("🚀 持续挖矿模式已启动...")
        self.continuous_mining_loop()

    def stop_continuous_mining(self):
        """停止持续挖矿模式"""
        if not self.is_mining_continous:
            return

        self.is_mining_continous = False
        self.start_cont_mine_button.config(state=NORMAL)
        self.stop_cont_mine_button.config(state=DISABLED)
        self.mine_button.config(state=NORMAL) # 恢复单次挖矿
        
        self.update_status_bar("🛑 持续挖矿模式已停止。")
        messagebox.showinfo("挖矿停止", "持续挖矿模式已停止。")
        self.update_display()

    def continuous_mining_loop(self):
        """持续挖矿的递归循环函数"""
        if not self.is_mining_continous:
            return

        try:
            block, elapsed = self.mine_block_logic()
            
            self.update_status_bar(f"⛏️ 持续挖矿中 | 发现新区块 #{block['index']} (用时: {elapsed:.2f}s) | 难度: {self.blockchain.get_difficulty()}")
            
            # 每找到一个块就刷新显示
            self.update_display()
            
        except Exception as e:
            print(f"持续挖矿错误: {e}")
            self.stop_continuous_mining()
            messagebox.showerror("持续挖矿错误", f"持续挖矿过程中发生错误并已停止: {e}")
            return
            
        # 使用 root.after 延迟调用自身，避免阻塞GUI
        self.root.after(self.mining_interval_ms, self.continuous_mining_loop)
            
    def save_data(self):
        if self.blockchain.save_chain(BLOCKCHAIN_FILENAME):
            messagebox.showinfo("保存成功", f"区块链数据已保存到 {BLOCKCHAIN_FILENAME}")
            self.update_status_bar(f"区块链数据已保存到 {BLOCKCHAIN_FILENAME}")
        else:
            messagebox.showerror("保存失败", "无法保存区块链。")

    def load_data(self):
        if messagebox.askyesno("加载数据", "这将覆盖当前所有未保存的进度，确定要加载吗？"):
            if self.blockchain.load_chain(BLOCKCHAIN_FILENAME):
                messagebox.showinfo("加载成功", f"已从 {BLOCKCHAIN_FILENAME} 加载数据。")
                self.update_status_bar(f"已从 {BLOCKCHAIN_FILENAME} 加载数据。")
                self.update_display()
            else:
                messagebox.showerror("加载失败", "无法加载区块链文件或文件损坏。")

    def validate_chain(self):
        self.update_status_bar("正在验证区块链完整性...")
        self.root.update_idletasks()
        if self.blockchain.is_chain_valid():
            messagebox.showinfo("验证结果", "✅ 区块链验证通过！完整性良好。")
            self.update_status_bar("验证通过。")
        else:
            messagebox.showerror("验证结果", "❌ 区块链验证失败！链条可能已被篡改。")
            self.update_status_bar("验证失败。")

    def about_us(self):
        aboutUs=easygui.ynbox(msg="""我是AnonUSAl，一个高中生，是业余编程爱好者。
这个程序是我一时兴起所编。
如你所见，目前该软件有很多bug。
由于bug太多，本人决定开源。
我希望结识一群志同道合的朋友们，并帮我们修正他们。
本人QQ：3353739856 电报：AnonUsAl
我的论坛地址：http://anonusal.tttttttttt.top""", title="关于我们", choices=("关于我们","软件更新",))
        aboutUrl = "http://anonusal.tttttttttt.top"
        updateUrl = "http://anonusal.github.io"
        if aboutUs:
            webbrowser.open(aboutUrl)
        else:
            webbrowser.open(updateUrl)
            
    def on_tab_change(self, event):
        """当 Tab 改变时触发更新显示"""
        self.update_display()

    def update_display(self):
        """更新所有文本框显示的内容"""
        current_tab_name = self.notebook.tab(self.notebook.select(), "text")
        
        # 1. 完整区块链 (Chain Tab)
        if current_tab_name == '完整区块链':
            self.chain_text.config(state=NORMAL)
            self.chain_text.delete(1.0, END)
            
            self.chain_text.insert(INSERT, f"--- T币 区块链 (总长: {len(self.blockchain.chain)} 区块) ---\n\n", "header")
            
            for block in reversed(self.blockchain.chain): # 倒序显示，最新的在最前面
                is_valid_hash = block['hash'][:self.blockchain.get_difficulty()] == '0' * self.blockchain.get_difficulty()
                
                self.chain_text.insert(INSERT, f"区块 #{block['index']} ", "block_index")
                self.chain_text.insert(INSERT, f" (矿工: {block['miner']})\n")
                
                self.chain_text.insert(INSERT, f"  时间戳: {time.ctime(block['timestamp'])}\n")
                self.chain_text.insert(INSERT, f"  哈希: {block['hash']}\n")
                self.chain_text.insert(INSERT, f"  前一哈希: {block['previous_hash']}\n")
                self.chain_text.insert(INSERT, f"  证明(Nonce): {block['proof']}\n")
                
                hash_tag = "valid_hash" if is_valid_hash else "invalid_hash"
                self.chain_text.insert(INSERT, f"  难度检查: {is_valid_hash} (需要 {self.blockchain.get_difficulty()} 个 '0')\n", hash_tag)
                
                self.chain_text.insert(INSERT, "  交易列表:\n", "transaction_header")
                
                if not block['transactions']:
                    self.chain_text.insert(INSERT, "    (无交易)\n")
                for tx in block['transactions']:
                    self.chain_text.insert(INSERT, f"    - {tx['sender']} -> {tx['recipient']} ({tx['amount']:.2f} T币)\n")
                self.chain_text.insert(INSERT, "-"*60 + "\n\n")
            
            # 配置标签样式
            self.chain_text.tag_config("header", foreground="#4CAF50", font=('Consolas', 11, 'bold'))
            self.chain_text.tag_config("block_index", foreground="#FFD700", font=('Consolas', 10, 'bold'))
            self.chain_text.tag_config("valid_hash", foreground="#00FF00")
            self.chain_text.tag_config("invalid_hash", foreground="#FF0000", font=('Consolas', 10, 'bold'))
            self.chain_text.tag_config("transaction_header", foreground="#ADD8E6")
            
            self.chain_text.config(state=DISABLED)

        # 2. 账户余额 (Balance Tab)
        elif current_tab_name == '账户余额':
            self.balance_text.config(state=NORMAL)
            self.balance_text.delete(1.0, END)
            
            self.balance_text.insert(INSERT, "--- T币 账户余额 (基于交易历史计算) ---\n\n", "header")
            balances = self.blockchain.get_all_balances()
            
            if not balances:
                self.balance_text.insert(INSERT, "(暂无交易记录)")
            else:
                sorted_balances = sorted(balances.items(), key=lambda item: item[1], reverse=True)
                for user, balance in sorted_balances:
                    color = "#008000" if balance >= 0 else "#FF0000"
                    
                    self.balance_text.insert(INSERT, f"{user.ljust(20)}: ", "user_name")
                    self.balance_text.insert(INSERT, f"{balance:.2f} T币\n", "balance_value")
                    self.balance_text.tag_config("user_name", font=('Consolas', 10, 'bold'))
                    self.balance_text.tag_config("balance_value", foreground=color, font=('Consolas', 10, 'bold'))
                    
            self.balance_text.config(state=DISABLED)
            
        # 3. 待处理交易 (Pending Tab)
        elif current_tab_name == '待处理交易':
            self.pending_text.config(state=NORMAL)
            self.pending_text.delete(1.0, END)
            
            self.pending_text.insert(INSERT, "--- 待处理 (待打包) 交易 ---\n\n", "header")
            
            if not self.blockchain.pending_transactions:
                self.pending_text.insert(INSERT, "(暂无待处理交易)")
            else:
                for tx in self.blockchain.pending_transactions:
                    self.pending_text.insert(INSERT, f"时间: {time.ctime(tx['timestamp'])}\n", "time")
                    self.pending_text.insert(INSERT, f"- {tx['sender']} -> {tx['recipient']} ({tx['amount']:.2f} T币)\n", "tx_detail")
                    self.pending_text.insert(INSERT, f"  签名: {tx['signature'][:20]}...\n\n", "signature")
            
            self.pending_text.tag_config("header", font=('Consolas', 10, 'bold'), foreground="#FFA500")
            self.pending_text.tag_config("time", foreground="#808080")
            self.pending_text.tag_config("tx_detail", font=('Consolas', 10, 'bold'))
            self.pending_text.config(state=DISABLED)
            
        # 更新状态栏余额和难度显示
        current_balance = self.blockchain.get_balance(self.miner_id)
        current_difficulty = self.blockchain.get_difficulty()
        self.difficulty_label.config(text=f"当前挖矿难度: {current_difficulty} ('0'开头)")
        
        if self.is_mining_continous:
             self.update_status_bar(f"⛏️ 持续挖矿中... | 钱包: {self.miner_id} | 余额: {current_balance:.2f} T币 | 待处理交易: {len(self.blockchain.pending_transactions)}")
        else:
            self.update_status_bar(f"就绪。| 钱包: {self.miner_id} | 余额: {current_balance:.2f} T币 | 待处理交易: {len(self.blockchain.pending_transactions)}")



# --- 主程序入口 ---
if __name__ == "__main__":
    # 使用自定义的 HTML 处理器创建服务器


    try:
        # 实例化区块链
        tcoin = Blockchain()
        
        # 启动GUI
        main_window = Tk()
        app = BlockchainApp(main_window, tcoin)
        main_window.mainloop()
        
    except Exception as e:
        easygui.msgbox(f"程序运行出错: {e}", title="警告")
        print(f"程序运行出错: {e}")
        # 确保程序退出时保存数据
        try:
            
             tcoin.save_chain(BLOCKCHAIN_FILENAME)

        except NameError:
             pass 
        input("按回车键退出...")
    # 使用自定义的 HTML 处理器创建服务器
