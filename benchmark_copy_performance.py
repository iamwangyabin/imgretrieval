#!/usr/bin/env python3
"""
性能对比脚本：Python 的 shutil.copy2 vs 系统级 cp 命令

对比项目：
1. shutil.copy2() - Python 标准库（organize_images_optimized.py 使用）
2. shutil.copy() - Python 标准库（更快的版本，不复制元数据）
3. os.system('cp') - 系统级 cp 命令
4. subprocess.run(['cp']) - 通过 subprocess 调用系统 cp
5. 多线程 shutil.copy2 - 使用 ThreadPoolExecutor
"""

import os
import sys
import time
import shutil
import subprocess
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from tqdm import tqdm
except ImportError:
    class tqdm:
        def __init__(self, iterable=None, total=None, desc=None, **kwargs):
            self.iterable = iterable
            self.total = total
            self.desc = desc
            self.count = 0
        
        def __iter__(self):
            for item in self.iterable:
                self.count += 1
                yield item
        
        def update(self, n=1):
            self.count += n


def create_test_files(test_dir, num_files=100, file_size_mb=1):
    """创建测试文件"""
    test_dir = Path(test_dir)
    test_dir.mkdir(exist_ok=True)
    
    print(f"创建 {num_files} 个测试文件（每个 {file_size_mb}MB）...")
    
    for i in range(num_files):
        file_path = test_dir / f"test_file_{i:04d}.bin"
        with open(file_path, 'wb') as f:
            f.write(os.urandom(file_size_mb * 1024 * 1024))
    
    print(f"✓ 创建完成\n")


def benchmark_shutil_copy2(source_dir, dest_dir, num_files):
    """测试 shutil.copy2 性能"""
    dest_dir = Path(dest_dir) / "shutil_copy2"
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    source_files = list(Path(source_dir).glob("*.bin"))[:num_files]
    
    start_time = time.time()
    for source_file in tqdm(source_files, desc="shutil.copy2", unit="个"):
        dest_file = dest_dir / source_file.name
        shutil.copy2(source_file, dest_file)
    
    elapsed = time.time() - start_time
    return elapsed, len(source_files)


def benchmark_shutil_copy(source_dir, dest_dir, num_files):
    """测试 shutil.copy 性能（更快，不复制元数据）"""
    dest_dir = Path(dest_dir) / "shutil_copy"
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    source_files = list(Path(source_dir).glob("*.bin"))[:num_files]
    
    start_time = time.time()
    for source_file in tqdm(source_files, desc="shutil.copy ", unit="个"):
        dest_file = dest_dir / source_file.name
        shutil.copy(source_file, dest_file)
    
    elapsed = time.time() - start_time
    return elapsed, len(source_files)


def benchmark_system_cp(source_dir, dest_dir, num_files):
    """测试系统 cp 命令性能"""
    dest_dir = Path(dest_dir) / "system_cp"
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    source_files = list(Path(source_dir).glob("*.bin"))[:num_files]
    
    start_time = time.time()
    for source_file in tqdm(source_files, desc="system_cp  ", unit="个"):
        dest_file = dest_dir / source_file.name
        os.system(f"cp '{source_file}' '{dest_file}' 2>/dev/null")
    
    elapsed = time.time() - start_time
    return elapsed, len(source_files)


def benchmark_subprocess_cp(source_dir, dest_dir, num_files):
    """测试通过 subprocess 调用 cp 的性能"""
    dest_dir = Path(dest_dir) / "subprocess_cp"
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    source_files = list(Path(source_dir).glob("*.bin"))[:num_files]
    
    start_time = time.time()
    for source_file in tqdm(source_files, desc="subprocess ", unit="个"):
        dest_file = dest_dir / source_file.name
        try:
            subprocess.run(['cp', str(source_file), str(dest_file)], 
                         capture_output=True, timeout=5)
        except Exception:
            pass
    
    elapsed = time.time() - start_time
    return elapsed, len(source_files)


def benchmark_multithreaded_copy2(source_dir, dest_dir, num_files, num_workers=4):
    """测试多线程 shutil.copy2 性能"""
    dest_dir = Path(dest_dir) / "multithreaded_copy2"
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    source_files = list(Path(source_dir).glob("*.bin"))[:num_files]
    
    def copy_task(source_file, dest_dir):
        dest_file = dest_dir / source_file.name
        shutil.copy2(source_file, dest_file)
    
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(copy_task, src, dest_dir) for src in source_files]
        with tqdm(total=len(futures), desc="multi_copy2", unit="个") as pbar:
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass
                pbar.update(1)
    
    elapsed = time.time() - start_time
    return elapsed, len(source_files)


def benchmark_batch_cp(source_dir, dest_dir, num_files):
    """测试批量 cp 命令（一次复制多个文件）"""
    dest_dir = Path(dest_dir) / "batch_cp"
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    source_files = list(Path(source_dir).glob("*.bin"))[:num_files]
    
    # 批量复制（每次10个文件）
    batch_size = 10
    start_time = time.time()
    
    with tqdm(total=len(source_files), desc="batch_cp   ", unit="个") as pbar:
        for i in range(0, len(source_files), batch_size):
            batch = source_files[i:i+batch_size]
            cmd = f"cp {' '.join(str(f) for f in batch)} '{dest_dir}/' 2>/dev/null"
            os.system(cmd)
            pbar.update(len(batch))
    
    elapsed = time.time() - start_time
    return elapsed, len(source_files)


def print_results(results):
    """打印对比结果"""
    print(f"\n{'='*70}")
    print(f"{'方法':<25} {'耗时':<15} {'吞吐量':<20}")
    print(f"{'='*70}")
    
    for method, elapsed, num_files in sorted(results, key=lambda x: x[1]):
        throughput = num_files / elapsed
        print(f"{method:<25} {elapsed:>8.2f}s       {throughput:>8.2f} 文件/秒")
    
    print(f"{'='*70}\n")
    
    # 找出最快的方法
    fastest = min(results, key=lambda x: x[1])
    slowest = max(results, key=lambda x: x[1])
    
    slowdown_ratio = slowest[1] / fastest[1]
    print(f"最快: {fastest[0]} ({fastest[1]:.2f}s)")
    print(f"最慢: {slowest[0]} ({slowest[1]:.2f}s)")
    print(f"相差: {slowdown_ratio:.2f}x\n")


def main():
    # 测试参数
    num_files = 50  # 复制文件数
    file_size_mb = 2  # 每个文件大小（MB）
    
    print("="*70)
    print("Python shutil vs 系统 cp 命令 性能对比")
    print("="*70)
    print(f"测试参数：{num_files} 个文件 × {file_size_mb}MB/个\n")
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        source_dir = tmpdir / "source"
        dest_dir = tmpdir / "dest"
        
        # 创建测试文件
        create_test_files(source_dir, num_files, file_size_mb)
        
        # 运行所有基准测试
        results = []
        
        print("\n开始性能测试...\n")
        
        # 1. shutil.copy2
        try:
            elapsed, count = benchmark_shutil_copy2(source_dir, dest_dir, num_files)
            results.append(("shutil.copy2()", elapsed, count))
        except Exception as e:
            print(f"shutil.copy2 失败: {e}\n")
        
        # 2. shutil.copy
        try:
            elapsed, count = benchmark_shutil_copy(source_dir, dest_dir, num_files)
            results.append(("shutil.copy()", elapsed, count))
        except Exception as e:
            print(f"shutil.copy 失败: {e}\n")
        
        # 3. 多线程 shutil.copy2
        try:
            elapsed, count = benchmark_multithreaded_copy2(source_dir, dest_dir, num_files, num_workers=4)
            results.append(("ThreadPool.copy2(4 workers)", elapsed, count))
        except Exception as e:
            print(f"多线程 copy2 失败: {e}\n")
        
        # 4. 系统 cp 命令
        try:
            elapsed, count = benchmark_system_cp(source_dir, dest_dir, num_files)
            results.append(("os.system(cp)", elapsed, count))
        except Exception as e:
            print(f"系统 cp 失败: {e}\n")
        
        # 5. subprocess cp
        try:
            elapsed, count = benchmark_subprocess_cp(source_dir, dest_dir, num_files)
            results.append(("subprocess.cp", elapsed, count))
        except Exception as e:
            print(f"subprocess cp 失败: {e}\n")
        
        # 6. 批量 cp
        try:
            elapsed, count = benchmark_batch_cp(source_dir, dest_dir, num_files)
            results.append(("batch_cp", elapsed, count))
        except Exception as e:
            print(f"批量 cp 失败: {e}\n")
        
        # 打印结果
        print_results(results)


if __name__ == '__main__':
    main()
