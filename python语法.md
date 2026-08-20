# Python 语法笔记

> 力扣刷题用，Python 3。内容按常用程度排序。

## 1. python vs python3

- 本质同一个语言，只是命令行两个入口名，历史遗留问题。
- Python 2 在 2020-01-01 停止维护；现在（2026）**接触到的代码几乎全是 Python 3**。
- 力扣用 Python 3。只需确认版本号是 3.x 即可，命令名无关紧要。

## 2. 基础类型与变量（无需声明类型）

```python
a = 10          # int 整数
b = 3.14        # float 浮点
c = "hello"     # str 字符串
d = True        # bool 布尔（首字母大写）
e = None        # 空值（不是 null）

x, y = 1, 2     # 一行赋值多个
x, y = y, x     # 交换值，不用临时变量
```

口语说的「数组」在 Python 里就是**列表 list**，力扣的 `List[int]` 就是「装 int 的列表」，元组一般不叫数组。

变量**不用声明**，第一次赋值就自动创建、类型由值推断；但**用之前必须先赋值**，否则报 `NameError`。

`d = {}` 也是**赋值**（初始化成空字典），不是声明——先给个初始值，后面才能 `d[key]=value`。Python 没有「声明」，只有「赋值」。

### 一行交换，不用临时变量

```python
a, b = b, a      # 交换两个值，不需要临时变量
```

对比 C 需要 `temp = a; a = b; b = temp`。Go 也支持 `a, b = b, a`。

力扣典型应用——翻转二叉树，直接交换左右子树，不用临时节点：

```python
root.left, root.right = root.right, root.left
```

### Optional：X 或 None

```python
from typing import Optional
Optional[ListNode]   # ListNode 或 None，力扣链表/树题标注"可能为空"
```

`Optional[X]` = 「X 或 None」，等价 `X | None`（Python 3.10+）。只是注解提示，运行时 Python 不检查。

## 3. 运算

```python
7 / 2    # 3.5   真除法，结果 float
7 // 2   # 3     整除（向下取整）
7 % 2    # 1     取余
2 ** 10  # 1024  幂运算
-7 // 2  # -4    注意：向下取整，不是向零取整
```

Python 没有 `++` / `--` 自增自减，用 `x += 1`（等价 `x = x + 1`）。

## 4. 字符串

```python
s = "abc"
s[0]         # 'a'
s[-1]        # 'c'
s[0:3]       # 'abc'
s[::-1]      # 'cba' 反转
len(s)       # 3
s.upper()
s.split(",")
",".join(["a","b"])   # 'a,b'
s.isdigit()  # 是否全数字
s.isalpha()  # 是否全字母
int("123"); str(123)
```

### 切片 s[start:stop:step]

三个参数依次是 **起始 / 结束 / 步长**，左闭右开 `[起:止)`。

```python
s[0:5:2]   # step=2 跳着取
s[::-1]    # step=-1 倒着走（反转）
```

### 排序拼接（字母异位词常用）

```python
sorted_s = ''.join(sorted(s))   # sorted(s) 得字符列表，''.join 拼回字符串
```

## 5. 列表 list vs 元组 tuple

**核心区别：可变 vs 不可变。**

| | 列表 list | 元组 tuple |
|---|---|---|
| 写法 | `[1, 2, 3]` | `(1, 2, 3)` |
| 能否修改 | ✅ 可变 | ❌ 不可变 |
| 增删 | ✅ `append`/`pop` | ❌ |
| 当字典键 | ❌ | ✅ |
| 内存/速度 | 稍慢 | 稍快 |

```python
lst = [1, 2, 3]
lst[0] = 9        # ✅

tup = (1, 2, 3)
tup[0] = 9        # ❌ TypeError
```

`return i, j` 返回的是元组 `(i, j)`。力扣基本用列表。

列表元素**可以混类型**（`[1, "a", 3.14]` 合法，不会报错），只是同类型方便处理。

### 列表常用操作

```python
nums = [1, 2, 3]
nums.append(4)          # 末尾加
nums.pop()              # 弹末尾
nums.pop(0)             # 弹下标 0
nums.insert(0, 9)       # 下标 0 插入 9
len(nums)
nums.sort()                      # 原地排序
nums.sort(reverse=True)
sorted(nums)                     # 返回新列表
max(nums); min(nums); sum(nums)
[0] * 10                        # 10 个 0
nums.index(20)                   # 找值第一次出现的下标（找不到报 ValueError）
```

### 复制列表（b = a 不是复制！）

想"不改变原列表，算出新的"，分两种方式：

**① 用本身就返回新列表的操作**（最常用，天然不改原列表）：

```python
a = [3, 1, 2]
b = sorted(a)          # 返回新列表，a 不变
b = a + [4]            # 拼接返回新列表
b = a[:]               # 切片返回新列表
b = [x * 2 for x in a] # 推导式返回新列表
```

原地改 vs 返回新的：

| 原地改（改 a） | 返回新的（a 不变） |
|---------------|-------------------|
| `a.sort()` | `sorted(a)` |
| `a.append(x)` | `a + [x]` |
| `a.reverse()` | `a[::-1]` |

**② 想"复制一份再改"，用拷贝**：

```python
b = a          # ❌ 同一个列表的另一个名字，改 b 也改 a
b = a.copy()   # ✅ 复制
b = a[:]       # ✅ 复制
b = list(a)    # ✅ 复制
```

> 嵌套列表时 `a.copy()` 只复制外层（浅拷贝），内层仍共享；深拷贝遇到再说。

## 6. 字典（哈希表，键值对）—— 重点

```python
d = {"name": "Tom", "age": 20}
d["name"]          # 取值
d["city"] = "北京" # 加键值对
d.get("a", 0)      # 取，不存在返回默认 0
"a" in d           # 判断键是否存在
del d["a"]
```

**key 规则**：

- key 必须**不可变**（字符串/数字/元组可以，列表不行）。
- key 不能重复，重复会覆盖。

### value 可以是任何类型（包括列表）

```python
d["age"] = 20        # 数字
d["name"] = "Tom"    # 字符串
d["group"] = [1,2,3] # 列表也行！value 不限于基础类型
```

### d[key] = value 的语义：新增 or 覆盖

- **key 不存在** → 新增键值对
- **key 已存在** → 覆盖这个 key 的 value

```python
d = {}
d["a"] = 1    # 新增：{'a': 1}
d["a"] = 2    # 覆盖：{'a': 2}
```

### keys / values / items 三方法

```python
d = {"a": 1, "b": 2, "c": 3}

d.keys()     # dict_keys(['a','b','c'])        所有键（keys 带 s）
d.values()   # dict_values([1,2,3])            所有值
d.items()    # dict_items([('a',1),('b',2),('c',3)])  所有键值对
```

遍历字典：

```python
for k in d:              # 默认遍历键
for k in d.keys():       # 等价上面
for v in d.values():     # 遍历值
for k, v in d.items():   # 键值一起
```

### 分组模式（value 是列表，力扣高频）

用「排序后的字符串」当 key，把同组单词装进 value 列表（groupAnagrams）：

```python
d = {}
for s in strs:
    key = "".join(sorted(s))   # 排序后作为键
    if key not in d:
        d[key] = []            # 第一次见，新建键值对，值是空列表
    d[key].append(s)           # 往这个列表里加元素
return list(d.values())        # 所有分组
```

拆解：

- `d[key] = []` → 新建「键 = key，值 = 空列表」的键值对
- `d[key].append(s)` → 取出 key 对应的列表，往里加元素
- `list(d.values())` → 把所有 value（各组列表）转成列表返回

### {} 的歧义

```python
{}           # 空字典
set()        # 空集合
{1, 2, 3}    # 有元素、没冒号 → 集合
{"a": 1}     # 有冒号（键值对）→ 字典
```

### 什么是哈希

哈希函数把数据算成「数字编号」，哈希表靠它实现 O(1) 查找。**字典 dict 和集合 set 底层就是哈希表**。算法里「用哈希」= 用 dict/set 做 O(1) 查找 / 去重 / 计数。

## 7. 集合

```python
s = set([1, 2, 2, 3])   # {1,2,3} 自动去重
s.add(4); s.remove(4)
a & b    # 交集
a | b    # 并集
a - b    # 差集
x in s   # O(1)
```

特点：

- 自动**去重**、**无序**
- 不能下标访问（`s[0]` 报错）
- 元素必须**不可变**（列表不能放进去）
- 空集合用 `set()`，`{}` 是空字典

## 8. 条件判断

```python
if x > 0:
    ...
elif x == 0:
    ...
else:
    ...

res = "正" if x > 0 else "负"   # 三元表达式，必须有 else
```

### 逻辑运算与单行写法

逻辑运算用单词：

```python
a and b    # 与（C 的 &&）
a or b     # 或（C 的 ||）
not a      # 非（C 的 !）
```

**`if`、`elif`、`else`、`for`、`while`、`def`、`class` 这些关键字后面都要跟冒号 `:`。**

if/else 的简单语句可以写在冒号后同一行，但**冒号不能少**：

```python
if x > 0: return x        # ✅
else: return None         # ✅（else 后面要有冒号）
# else return None        # ❌ 缺冒号，语法错误
```

整段 if-else 一行，用三元表达式：`return x if x > 0 else None`。

## 9. 循环（重点）

### 通用格式

```python
for 变量 in 可迭代对象:
    循环体
```

- **`for` 后面**：放变量名（接住每次取出的元素）
- **`in` 后面**：放「可迭代对象」，常见有 range、列表、字符串、字典、enumerate、zip 等
- 取出的元素是**元组**时，用多个变量解包：`for i, v in enumerate(nums)`

**Python 没有 C 风格 `for(int i=0; i<n; i++)` 三段式**，`for` 是「遍历」语义。

### range() —— 生成数字序列，参数是**数字**不是数组名

```python
range(5)          # 0,1,2,3,4
range(1, 5)       # 1,2,3,4
range(0, 10, 2)   # 0,2,4,6,8
```

### range vs enumerate 怎么选

| 写法 | 什么时候用 |
|------|-----------|
| `for v in nums` | 只要值 |
| `for i, v in enumerate(nums)` | 要下标+值，**有数组** |
| `for i in range(n)` | 循环 n 次 / 生成数字，**可能没有数组** |
| `for i in range(len(nums))` | 要下标（可用 enumerate 替代） |

### 双重循环（内层依赖外层）

```python
# C++ for(int j=i+1; j<n; j++) 对应：
for i in range(n):
    for j in range(i + 1, n):
        ...
```

## 10. 函数

```python
def add(a, b=0):
    return a + b
```

### 传参：函数里改参数，外面会不会变？

核心结论：能不能"带回来"，取决于两点——**对象是否可变** + **是原地改还是重新赋值**。

| 操作 | 外面能变吗 |
|------|-----------|
| `nums[i] = x`、`nums.append(x)`、`d[k] = x` | ✅ 能（改内容） |
| `nums = [...]`（重新赋值） | ❌ 不能 |
| `x = 5`（int/str 重新赋值） | ❌ 不能 |

**原理**：Python 传的是「对象引用」——函数里的参数和外面的变量指向**同一个对象**。

- **改内容** → 改的是共享的那个对象 → 两边都看到变化
- **重新赋值** → 只是让函数里的名字指向新对象，外面的还指着原来的 → 外面不变

```python
def f(nums):
    nums.append(4)    # 改内容，带回来
a = [1, 2]
f(a)
print(a)             # [1, 2, 4]

def g(nums):
    nums = [9, 9]     # 重新赋值，带不回来
b = [1, 2]
g(b)
print(b)             # [1, 2]
```

**力扣 in-place 题**（如 moveZeroes）：必须用「改内容」（`nums[i]=`、`append`），不能 `nums = 新列表`，否则外面收不到。

**为什么不能"都自动能改"？** 为了安全和可预测性。如果所有参数都能被函数随意改，你就不知道哪个函数偷偷改了你的数据，代码难调试、并发还容易出问题。所以各语言要权衡「默认安全」和「默认方便」：

| 语言 | 默认 | 想原地改 |
|------|------|---------|
| C | 值传递 | 显式传指针 `int*` |
| Go | 值传递 | 显式传指针 `*T`（slice/map 是引用类型例外） |
| Java | 基本类型值传递，对象引用 | 对象能改内容 |
| Python | 都传引用 | 靠可变/不可变自动区分 |

Python 的巧妙之处：都传引用，但 `int`/`str` 不可变（自动等于值传递，安全）、`list`/`dict` 可变（自动等于引用，方便），所以不用像 C/Go 那样写 `*` 指针。

### 类 class 与 __init__（重点）

力扣链表/二叉树题会先给你结构：

```python
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
```

**`__init__` = 构造方法**，创建对象时自动调用。里面：

- **参数**（`val`/`left`/`right`）= 从外面传进来的值（输入）
- **`self.xxx`** = 对象的属性（存储）

`self.val = val` 意思是「把参数 val 的值，存到这个对象的 val 属性上」。

**self 是什么**：

- `self` = 对象在类内部的自称（`__init__` 里创建的那个对象）
- `node` = 对象外部的变量名（一个引用，指向这个对象）

`node = TreeNode(5)` 时，`TreeNode(5)` 调 `__init__`，里面的 `self` 就是那个新对象，返回后赋给 `node`——`node` 和 `self` 指向同一个对象。

**self.xxx 个数可以比参数多**：参数是输入，属性想挂几个挂几个：

```python
def __init__(self, val=0, left=None, right=None):
    self.val = val
    self.left = left
    self.right = right
    self.count = 0      # 额外属性，不是从参数来的
```

**调用类里的方法必须用 self 或实例点出来**：

```python
class Solution:
    def invertTree(self, root):
        self.invertTree(root.left)   # ✅ 类内部用 self 点出来
        # invertTree(root.left)      # ❌ 方法名在类命名空间里，直接写找不到

node.invertTree(root)                # 类外部用实例点出来
```

Python 会自动把 self 作为第一个参数传进去，所以递归里只写 `self.invertTree(root.left)`。

### Python 没有指针

没有 `*`、`&`、`->`、指针运算。变量本质是「引用」，指向对象。链表的 `next`、树的 `left`/`right` 就是引用，作用等同指针，只是不用写 `*` 和 `->`。

## 11. 列表推导式

```python
[x*x for x in range(10)]
[x for x in nums if x % 2 == 0]
[[0] * n for _ in range(m)]   # 二维数组（不能用 [[0]*n]*m）
```

## 12. 常用技巧

```python
float('inf')      # 正无穷，初始最大值
ord('a')          # 97
chr(97)           # 'a'
divmod(10, 3)     # (3, 1)
bin(10)           # '0b1010'
abs(-5)
```

## 13. 常见坑

1. **二维数组**：`[[0]*n for _ in range(m)]`，不能用 `[[0]*n]*m`（每行是同一引用）。
2. **可变对象当默认参数**：`def f(lst=[])` 危险，应 `def f(lst=None)`。
3. **`len` 不是 `lens`**：Python/Go 都是 `len()`；C++ 是 `.size()`/`std::size()`；`lens` 任何语言都不是。
4. **`return i, j` 是元组**，力扣要求 `List[int]` 时要用 `return [i, j]`。
5. **条件在 return 前**：`if cond: return x`，不能写 `return x if cond`（三元缺 else 会 SyntaxError）。
6. **`list.index(x)` 找不到抛 ValueError**（O(n)）；字符串 `find()` 找不到返回 -1。
7. 手打代码注意中文逗号 `，` 要写成英文 `,`。
8. **Python 严格区分大小写**：`list` ≠ `List`，`x` ≠ `X`。
9. **`list`（小写）是内置函数，`List`（大写）是 typing 注解用**：`return list(...)`，不能写 `return List(...)`。
10. **别用内置名当变量名**：`dict = {}`、`list = []` 会覆盖内置类型，之后 `dict()`/`list()` 会报错。
11. **for 遍历区间用 `range(start, stop)`**，不能写 `(start:stop)`（切片冒号语法不能用在 for 里，会 SyntaxError）。

## 14. 查值拿下标的惯用法

`index()` 是 O(n)，频繁查用字典 O(1)。

**例子 1：单次查找，用 `.index()` 够用**

```python
nums = [10, 20, 30, 40]
pos = nums.index(30)   # 2，找到 30 的下标
```

**例子 2：力扣「值 → 下标」反复查，用字典 O(1)**

```python
# 比如 twoSum：给一个值，要它的下标
nums = [2, 7, 11, 15]

# 慢：每次查都 O(n) 扫一遍
idx = nums.index(7)          # 1

# 好：先建字典，之后每次 O(1)
d = {v: i for i, v in enumerate(nums)}   # {2:0, 7:1, 11:2, 15:3}
idx = d[7]                   # 1
```

## 15. 与其他语言的语法差异（C++ / Go）

| 概念 | Python | C++ / Go |
|------|--------|----------|
| 逻辑与 / 或 / 非 | `and` / `or` / `not` | `&&` / `\|\|` / `!` |
| 自增 / 自减 | 无，用 `x += 1` | `x++` / `x--` |
| 布尔值 | `True` / `False` | `true` / `false` |
| 空值 | `None` | `nullptr`(C++) / `nil`(Go) |
| 整除 | `//` | `/`（整数相除自动取整） |
| 幂运算 | `**` | 无，用 `pow()` |
| 三元表达式 | `a if 条件 else b` | `条件 ? a : b`（Go 没有） |
| 注释 | `#` | `//` |
| 代码块 | 缩进 | `{}` |
| 交换两值 | `a, b = b, a` | 需临时变量（Go 支持） |
