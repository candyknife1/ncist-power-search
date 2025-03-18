from flask import Flask, render_template, request, jsonify
from pyecharts.charts import Bar, Scatter,Pie
from pyecharts import options as opts
from pyecharts.globals import CurrentConfig, NotebookType
from pyecharts.charts import Page
from datetime import datetime
import json
import time
from pathlib import Path
import glob
import os
from flask_cors import CORS
from threading import Thread, Lock

from api import 完美校园

app = Flask(__name__, static_folder='web', static_url_path='')
CORS(app)
api = 完美校园(phone_num='13625696883',password='12346789vb',device_id='5745286925431029')

# 全局变量
lock = Lock()
page = 0

class server:

    # 使用pyecharts实际上是一个非常不明智的选择，echarts.js 才是正确选择@！@！！
    def render(self):
        try:
            # 先更新数据
            self.update_power_data()
            
            # 从保存的电量数据文件中读取数据
            power_data = {'一号公寓空调': [], '七号公寓空调': []}
            building_ids = {'一号公寓空调': '9', '七号公寓空调': '4'}  # 根据实际的building_id填写
            
            for building_name, building_id in building_ids.items():
                power_file = f'data/power_{building_id}.json'
                if os.path.exists(power_file):
                    with open(power_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # 将房间数据按楼层排序
                        sorted_rooms = sorted(data['rooms'], key=lambda x: x['room_name'])
                        power_data[building_name] = sorted_rooms
            
            # 处理数据用于图表显示
            _data = []  # 楼栋名称
            x_data = [[], []]  # 房间号
            y_data = [[], []]  # 电量数据
            
            # 处理一号公寓数据
            if power_data['一号公寓空调']:
                _data.append('一号公寓空调')
                abnormal_rooms = []  # 记录异常房间
                for room in power_data['一号公寓空调']:
                    quantity = float(room['quantity'])
                    # 检查异常电量
                    if quantity < 0 or quantity > 300:
                        abnormal_rooms.append(f"{room['room_name']}({quantity}度)")
                        quantity = 0  # 将异常值设为0
                    x_data[0].append(room['room_name'])
                    y_data[0].append(quantity)
                if abnormal_rooms:
                    print(f"一号公寓异常电量房间: {', '.join(abnormal_rooms)}")
            
            # 处理七号公寓数据
            if power_data['七号公寓空调']:
                _data.append('七号公寓空调')
                abnormal_rooms = []  # 记录异常房间
                for room in power_data['七号公寓空调']:
                    quantity = float(room['quantity'])
                    # 检查异常电量
                    if quantity < 0 or quantity > 300:
                        abnormal_rooms.append(f"{room['room_name']}({quantity}度)")
                        quantity = 0  # 将异常值设为0
                    x_data[1].append(room['room_name'])
                    y_data[1].append(quantity)
                if abnormal_rooms:
                    print(f"七号公寓异常电量房间: {', '.join(abnormal_rooms)}")

            # 创建散点图
            scatter = (
                Scatter()
                .add_xaxis(x_data[0])
                .add_yaxis(_data[0], y_data[0], symbol="circle", 
                           label_opts=opts.LabelOpts(is_show=False))
                .add_yaxis(_data[1], y_data[1], symbol="circle", 
                           label_opts=opts.LabelOpts(is_show=False))
                .set_global_opts(
                    title_opts=opts.TitleOpts(
                        title="一号公寓与七号公寓剩余电量对比",
                        subtitle="注：电量小于0度或大于300度的房间已被设为0度",
                        pos_left="center"
                    ),
                    legend_opts=opts.LegendOpts(pos_right="right", pos_top="top"),
                    xaxis_opts=opts.AxisOpts(name="房间号"),
                    yaxis_opts=opts.AxisOpts(
                        name="剩余电量(度)",
                        min_=0,  # 设置y轴最小值
                        max_=300  # 设置y轴最大值
                    )
                )
            )

            # 计算并创建柱状图
            part_powers = [[], []]  # 一号公寓和七号公寓的数据
            for i, building_data in enumerate([power_data['一号公寓空调'], power_data['七号公寓空调']]):
                floor_data = [[] for _ in range(6)]  # 6层楼
                abnormal_count = [0] * 6  # 记录每层异常房间数
                total_count = [0] * 6  # 记录每层总房间数
                
                for room in building_data:
                    try:
                        floor = int(room['room_name'][0]) - 1  # 根据房间号第一位确定楼层
                        quantity = float(room['quantity'])
                        total_count[floor] += 1
                        
                        # 检查异常电量
                        if quantity < 0 or quantity > 300:
                            abnormal_count[floor] += 1
                            quantity = 0  # 将异常值设为0
                        floor_data[floor].append(quantity)
                        
                    except (ValueError, IndexError):
                        print(f"无法解析房间号: {room['room_name']}")
                
                # 计算每层的平均值并记录异常数据
                part_powers[i] = []
                for floor_num, (floor, count, total) in enumerate(zip(floor_data, abnormal_count, total_count)):
                    avg = round(sum(floor)/len(floor) if floor else 0, 2)
                    part_powers[i].append(avg)
                    if count > 0:
                        print(f"{_data[i]}第{floor_num+1}层有 {count}/{total} 个房间电量异常")

            # 创建柱状图
            bar = (
                Bar()
                .add_xaxis([f"第{i+1}层" for i in range(6)])
                .add_yaxis(_data[0], part_powers[0])
                .add_yaxis(_data[1], part_powers[1])
                .set_global_opts(
                    title_opts=opts.TitleOpts(
                        title="楼层平均电量对比",
                        subtitle="注：电量小于0度或大于300度的房间已被设为0度计算平均值",
                        pos_left="center"
                    ),
                    legend_opts=opts.LegendOpts(pos_right="right", pos_top="top"),
                    xaxis_opts=opts.AxisOpts(name="楼层"),
                    yaxis_opts=opts.AxisOpts(
                        name="平均剩余电量(度)",
                        min_=0,  # 设置y轴最小值
                        max_=300  # 设置y轴最大值
                    )
                )
            )

            # 创建页面并添加图表
            page = Page()
            page.add(scatter, bar)
            page.render("web/chart.html")
            print("图表已更新")

        except Exception as e:
            print(f"渲染图表时出错: {e}")

    @app.route('/')
    def index():
        with open('web/index.html', 'r', encoding='UTF-8') as f:
            html_content = f.read()
        return html_content

    @app.route('/get_buildings')
    def get_buildings():
        buildings = []
        try:
            for file_path in glob.glob('data/building_*.json'):
                with open(file_path, 'r') as f:
                    building_data = json.load(f)
                    buildings.append({
                        'name': building_data['name']
                    })
            return jsonify(buildings)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/query', methods=['POST'])
    def query():
        data = request.json
        building_name = data.get('building')
        room_number = data.get('room')
        
        # 验证输入
        if not building_name or not room_number:
            return jsonify({'error': '请输入完整信息'})
        
        # 查找对应的房间ID
        room_id = None
        for file_path in glob.glob('data/building_*.json'):
            try:
                with open(file_path, 'r') as f:
                    building_data = json.load(f)
                    if building_data['name'] == building_name:
                        for room in building_data['rooms']:
                            if room['name'] == room_number:
                                room_id = room['id']
                                break
                        break
            except Exception as e:
                print(f"读取楼栋数据失败: {e}")
        
        if not room_id:
            return jsonify({'error': '未找到该房间信息'})
        
        # 查询电费
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        res, msg = api.get_power_info(room_id)
        
        if res:
            if msg.get('returncode') == '100':
                return jsonify({
                    'quantity': f"{msg['quantity']} {msg['quantityunit']}",
                    'currentTime': current_time
                })
            return jsonify({'error': msg.get('returnmsg', '查询失败')})
        return jsonify({'error': str(msg)})

    def test_get_parts(self):
        # 使用已有的api实例而不是创建新实例
        res, msg = api.get_part_id()
        if res:
            print("获取公寓列表成功:")
            print("完整返回数据:", msg)

            # 保存到文件
            try:
                with open('data/parts.json', 'w+') as f:
                    json.dump(msg, f, indent=4)
                print("\n数据已保存到 data/parts.json")
            except Exception as e:
                print(f"\n保存文件失败: {e}")
        else:
            print(f"获取失败: {msg}")

    def test_get_unitid(self):
        # 先获取公寓列表
        res, msg = api.get_part_id()
        if not res:
            print("获取公寓列表失败:", msg)
            return
        
        # 遍历每个公寓
        for part in msg['roomlist']:
            part_id = part['id']
            part_name = part['name']
            print(f"\n正在获取{part_name}(ID:{part_id})的单元列表...")
            
            # 获取该公寓的单元列表
            res, units = api.get_unitid(part_id)
            if res:
                print(f"{part_name}的单元列表:")
                print(units)
                
                # 保存到文件
                try:
                    with open(f'data/units_{part_id}.json', 'w+') as f:
                        json.dump(units, f, indent=4)
                    print(f"单元数据已保存到 data/units_{part_id}.json")
                except Exception as e:
                    print(f"保存文件失败: {e}")
            else:
                print(f"获取{part_name}的单元列表失败: {units}")
            
            time.sleep(2)

    def test_get_rooms(self):
        # 先获取公寓列表
        res, msg = api.get_part_id()
        if not res:
            print("获取公寓列表失败:", msg)
            return
        
        # 遍历每个公寓
        for part in msg['roomlist']:
            part_id = part['id']
            part_name = part['name']
            
            # 获取该公寓的楼层ID
            res, level = api.get_levelid(part_id)
            if not res:
                print(f"获取{part_name}的楼层ID失败:", level)
                continue
            
            # 获取该楼层的房间列表
            level_id = level['roomlist'][0]['id']  # 获取楼层ID
            res, rooms = api.get_room_list(part_id, level_id)
            if res:
                print(f"\n正在获取{part_name}的房间列表...")
                print(f"{part_name}的房间列表:")
                print(rooms)
                
                # 保存到文件
                try:
                    building_data = {
                        'name': part_name,
                        'buildid': part_id,
                        'levelid': level_id,
                        'rooms': rooms['roomlist']
                    }
                    with open(f'data/building_{part_id}.json', 'w+') as f:
                        json.dump(building_data, f, indent=4)
                    print(f"房间数据已保存到 data/building_{part_id}.json")
                except Exception as e:
                    print(f"保存文件失败: {e}")
            else:
                print(f"获取{part_name}的房间列表失败: {rooms}")
            
            time.sleep(2)

    def init_building_data(self):
        """
        初始化建筑数据。
        只有在没有building_*.json文件时才会执行完整的数据获取流程。
        """
        # 检查是否已存在building数据文件
        if list(Path('data').glob('building_*.json')):
            print("已存在建筑数据文件，跳过初始化")
            return
        
        print("未找到建筑数据文件，开始初始化...")
        
        # 1. 获取公寓列表
        res, msg = api.get_part_id()
        if not res:
            print("获取公寓列表失败:", msg)
            return
        
        print("获取公寓列表成功")
        
        # 保存公寓列表
        try:
            with open('data/parts.json', 'w+') as f:
                json.dump(msg, f, indent=4)
        except Exception as e:
            print(f"保存公寓列表失败: {e}")
            return
        
        # 2. 遍历每个公寓获取房间信息
        for part in msg['roomlist']:
            part_id = part['id']
            part_name = part['name']
            print(f"\n处理{part_name}(ID:{part_id})...")
            
            # 获取楼层ID
            res, level = api.get_levelid(part_id)
            if not res:
                print(f"获取{part_name}的楼层ID失败:", level)
                continue
            
            # 获取房间列表
            level_id = level['roomlist'][0]['id']
            res, rooms = api.get_room_list(part_id, level_id)
            if not res:
                print(f"获取{part_name}的房间列表失败:", rooms)
                continue
            
            # 保存数据
            try:
                building_data = {
                    'name': part_name,
                    'buildid': part_id,
                    'levelid': level_id,
                    'rooms': rooms['roomlist']
                }
                with open(f'data/building_{part_id}.json', 'w+') as f:
                    json.dump(building_data, f, indent=4)
                print(f"已保存{part_name}的数据")
            except Exception as e:
                print(f"保存{part_name}数据失败: {e}")
            
            time.sleep(2)
        
        print("\n建筑数据初始化完成")

    def update_power_data(self):
        """
        更新电量数据，每7天更新一次
        只有在成功更新数据后才记录更新时间
        """
        try:
            # 检查上次更新时间
            last_update = None
            if os.path.exists('data/last_update.json'):
                with open('data/last_update.json', 'r') as f:
                    last_update = datetime.fromisoformat(json.load(f)['time'])
            
            current_time = datetime.now()
            
            # 如果是首次更新或距离上次更新超过7天
            if not last_update or (current_time - last_update).days >= 7:
                print("开始更新电量数据...")
                
                # 查找一号公寓和七号公寓的数据
                target_buildings = []
                required_buildings = {'一号公寓空调', '七号公寓空调'}
                found_buildings = {}

                # 读取所有房间数据
                for file_path in glob.glob('data/building_*.json'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        building_data = json.load(f)
                        building_name = building_data['name']
                        if building_name in required_buildings and building_name not in found_buildings:
                            found_buildings[building_name] = {
                                'buildid': building_data['buildid'],
                                'name': building_name,
                                'rooms': building_data['rooms']
                            }

                target_buildings = list(found_buildings.values())
                
                if len(target_buildings) != 2:
                    missing = required_buildings - set(found_buildings.keys())
                    raise Exception(f"未找到所有需要的建筑 (缺少: {missing})")
                
                update_success = True
                
                # 更新这两栋楼的数据
                for building in target_buildings:
                    try:
                        # 获取该楼所有房间ID
                        room_ids = [room['id'] for room in building['rooms']]
                        
                        print(f"正在更新 {building['name']} 的电量数据...")
                        print(f"房间数量: {len(room_ids)}")
                        
                        # 存储该楼的电量数据
                        power_data = []
                        
                        # 直接查询每个房间的电量
                        total_rooms = len(building['rooms'])
                        for index, room in enumerate(building['rooms'], 1):
                            try:
                                room_id = room['id']
                                print(f"[{index}/{total_rooms}] 正在查询 {room['name']} 房间...")
                                res, msg = api.get_power_info(room_id)
                                if not res:
                                    print(f"    [失败] 获取房间 {room_id} 电量失败")
                                    continue
                                    
                                if msg.get('returncode') == '100':
                                    quantity = float(msg['quantity'])
                                    # 检查异常电量
                                    if quantity < 0 or quantity > 300:
                                        print(f"    [异常] {room['name']} 房间电量异常: {quantity}度，已置为0")
                                        quantity = 0  # 将异常值设为0
                                    
                                    power_data.append({
                                        'room_id': room_id,
                                        'room_name': room['name'],
                                        'quantity': str(quantity),  # 转回字符串保持格式一致
                                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    })
                                    print(f"    [成功] {room['name']} 房间电量: {quantity} {msg['quantityunit']}")
                                else:
                                    print(f"    [错误] {room['name']} 房间查询失败: {msg.get('returnmsg', '未知错误')}")
                                
                                time.sleep(4)  # 避免请求过快
                            except Exception as e:
                                print(f"    [错误] 查询房间 {room_id} 时出错: {e}")
                        
                        # 保存电量数据到文件
                        if power_data:
                            power_file = f'data/power_{building["buildid"]}.json'
                            try:
                                with open(power_file, 'w', encoding='utf-8') as f:
                                    json.dump({
                                        'building_name': building['name'],
                                        'building_id': building['buildid'],
                                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                        'rooms': power_data
                                    }, f, indent=4, ensure_ascii=False)
                                print(f"已保存 {building['name']} 的电量数据")
                            except Exception as e:
                                print(f"保存 {building['name']} 电量数据失败: {e}")
                                update_success = False
                        else:
                            print(f"未获取到 {building['name']} 的有效电量数据")
                            update_success = False
                        
                        print(f"完成更新 {building['name']} 的电量数据")
                        
                    except Exception as e:
                        print(f"更新 {building['name']} 数据失败: {e}")
                        update_success = False
                
                # 只有在所有数据都成功更新后才保存更新时间
                if update_success:
                    with open('data/last_update.json', 'w') as f:
                        json.dump({'time': current_time.isoformat()}, f)
                    print("电量数据更新完成，已记录更新时间")
                else:
                    print("部分数据更新失败，不记录更新时间")
                    if os.path.exists('data/last_update.json'):
                        os.remove('data/last_update.json')
                    
            else:
                print(f"距离上次更新未满7天，跳过更新（还需等待{7-(current_time-last_update).days}天）")
            
        except Exception as e:
            print(f"更新数据时出错: {e}")
            if os.path.exists('data/last_update.json'):
                os.remove('data/last_update.json')

    @app.route('/get_chart_data')
    def get_chart_data():
        """获取图表数据的接口"""
        try:
            # 从保存的电量数据文件中读取数据
            power_data = {'一号公寓空调': [], '七号公寓空调': []}
            building_ids = {'一号公寓空调': '9', '七号公寓空调': '4'}
            
            for building_name, building_id in building_ids.items():
                power_file = f'data/power_{building_id}.json'
                if os.path.exists(power_file):
                    with open(power_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # 将房间数据按楼层排序
                        sorted_rooms = sorted(data['rooms'], key=lambda x: x['room_name'])
                        power_data[building_name] = sorted_rooms

            # 处理数据用于图表显示
            scatter_data = {
                'buildings': [],  # 楼栋名称
                'data': []  # 每栋楼的数据
            }
            bar_data = {
                'buildings': [],  # 楼栋名称
                'floors': [f"第{i+1}层" for i in range(6)],  # 楼层
                'data': []  # 每栋楼的数据
            }

            # 处理每栋楼的数据
            for building_name in ['一号公寓空调', '七号公寓空调']:
                if power_data[building_name]:
                    scatter_data['buildings'].append(building_name)
                    building_scatter_data = []
                    floor_data = [[] for _ in range(6)]  # 6层楼
                    
                    # 处理每个房间的数据
                    for room in power_data[building_name]:
                        quantity = float(room['quantity'])
                        # 检查异常电量
                        if quantity < 0 or quantity > 300:
                            quantity = 0
                        
                        # 添加散点图数据
                        building_scatter_data.append({
                            'room': room['room_name'],
                            'quantity': quantity
                        })
                        
                        # 添加柱状图数据
                        try:
                            floor = int(room['room_name'][0]) - 1
                            floor_data[floor].append(quantity)
                        except (ValueError, IndexError):
                            print(f"无法解析房间号: {room['room_name']}")
                    
                    scatter_data['data'].append(building_scatter_data)
                    
                    # 计算每层平均值
                    floor_averages = [
                        round(sum(floor)/len(floor) if floor else 0, 2)
                        for floor in floor_data
                    ]
                    bar_data['data'].append(floor_averages)
                    if building_name not in bar_data['buildings']:
                        bar_data['buildings'].append(building_name)

            # 返回处理后的数据
            return jsonify({
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'scatter_data': scatter_data,  # 散点图数据
                'bar_data': bar_data,  # 柱状图数据
                'note': '电量小于0度或大于300度的房间已被设为0度'
            })

        except Exception as e:
            print(f"获取图表数据时出错: {e}")
            return jsonify({'error': str(e)}), 500

    def update_all_buildings_power_data(self):
        """
        更新所有楼栋的电量数据（除了一号公寓和七号公寓）
        每7天更新一次
        """
        try:
            # 创建数据目录（如果不存在）
            os.makedirs('data', exist_ok=True)
            
            # 检查上次更新时间
            last_update = None
            if os.path.exists('data/all_buildings_last_update.json'):
                with open('data/all_buildings_last_update.json', 'r') as f:
                    last_update = datetime.fromisoformat(json.load(f)['time'])
            
            current_time = datetime.now()
            
            # 如果是首次更新或距离上次更新超过7天
            if not last_update or (current_time - last_update).days >= 7:
                print("开始更新所有楼栋电量数据...")
                
                # 获取所有楼栋数据
                all_buildings = []
                excluded_buildings = {'一号公寓空调', '七号公寓空调'}
                
                # 读取所有房间数据
                for file_path in glob.glob('data/building_*.json'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        building_data = json.load(f)
                        building_name = building_data['name']
                        if building_name not in excluded_buildings:
                            all_buildings.append({
                                'buildid': building_data['buildid'],
                                'name': building_name,
                                'rooms': building_data['rooms']
                            })
                
                if not all_buildings:
                    print("未找到需要更新的楼栋")
                    return
                
                update_success = True
                
                # 更新每栋楼的数据
                for building in all_buildings:
                    try:
                        print(f"正在更新 {building['name']} 的电量数据...")
                        print(f"房间数量: {len(building['rooms'])}")
                        
                        # 存储该楼的电量数据
                        power_data = []
                        
                        # 直接查询每个房间的电量
                        total_rooms = len(building['rooms'])
                        for index, room in enumerate(building['rooms'], 1):
                            try:
                                room_id = room['id']
                                print(f"[{index}/{total_rooms}] 正在查询 {room['name']} 房间...")
                                res, msg = api.get_power_info(room_id)
                                if not res:
                                    print(f"    [失败] 获取房间 {room_id} 电量失败")
                                    continue
                                    
                                if msg.get('returncode') == '100':
                                    quantity = float(msg['quantity'])
                                    # 检查异常电量
                                    if quantity < 0 or quantity > 300:
                                        print(f"    [异常] {room['name']} 房间电量异常: {quantity}度，已置为0")
                                        quantity = 0  # 将异常值设为0
                                    
                                    power_data.append({
                                        'room_id': room_id,
                                        'room_name': room['name'],
                                        'quantity': str(quantity),  # 转回字符串保持格式一致
                                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    })
                                    print(f"    [成功] {room['name']} 房间电量: {quantity} {msg['quantityunit']}")
                                else:
                                    print(f"    [错误] {room['name']} 房间查询失败: {msg.get('returnmsg', '未知错误')}")
                                
                                time.sleep(4)  # 避免请求过快
                            except Exception as e:
                                print(f"    [错误] 查询房间 {room_id} 时出错: {e}")
                        
                        # 保存电量数据到文件
                        if power_data:
                            power_file = f'data/power_{building["buildid"]}.json'
                            try:
                                with open(power_file, 'w', encoding='utf-8') as f:
                                    json.dump({
                                        'building_name': building['name'],
                                        'building_id': building['buildid'],
                                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                        'rooms': power_data
                                    }, f, indent=4, ensure_ascii=False)
                                print(f"已保存 {building['name']} 的电量数据")
                            except Exception as e:
                                print(f"保存 {building['name']} 电量数据失败: {e}")
                                update_success = False
                        else:
                            print(f"未获取到 {building['name']} 的有效电量数据")
                            update_success = False
                        
                        print(f"完成更新 {building['name']} 的电量数据")
                        
                        # 每栋楼更新完成后，立即更新该楼的更新时间
                        with open(f'data/building_update_{building["buildid"]}.json', 'w') as f:
                            json.dump({'time': datetime.now().isoformat()}, f)
                        
                    except Exception as e:
                        print(f"更新 {building['name']} 数据失败: {e}")
                        update_success = False
                
                # 只有在所有数据都成功更新后才保存总的更新时间
                if update_success:
                    with open('data/all_buildings_last_update.json', 'w') as f:
                        json.dump({'time': current_time.isoformat()}, f)
                    print("所有楼栋电量数据更新完成，已记录更新时间")
                else:
                    print("部分数据更新失败，不记录总的更新时间")
                    
            else:
                print(f"距离上次更新未满7天，跳过更新（还需等待{7-(current_time-last_update).days}天）")
            
        except Exception as e:
            print(f"更新所有楼栋数据时出错: {e}")
    
    @app.route('/get_building_power', methods=['GET'])
    def get_building_power():
        """获取指定楼栋的电量数据"""
        try:
            building_name = request.args.get('building')
            
            if not building_name:
                return jsonify({'error': '请提供楼栋名称'}), 400
            
            # 查找对应的楼栋ID
            building_id = None
            for file_path in glob.glob('data/building_*.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    building_data = json.load(f)
                    if building_data['name'] == building_name:
                        building_id = building_data['buildid']
                        break
            
            if not building_id:
                return jsonify({'error': '未找到该楼栋信息'}), 404
            
            # 检查电量数据文件是否存在
            power_file = f'data/power_{building_id}.json'
            if not os.path.exists(power_file):
                return jsonify({'error': '该楼栋电量数据未更新'}), 404
            
            # 读取电量数据
            with open(power_file, 'r', encoding='utf-8') as f:
                power_data = json.load(f)
            
            # 返回处理后的数据
            return jsonify({
                'building_name': power_data['building_name'],
                'update_time': power_data['update_time'],
                'rooms': power_data['rooms']
            })
            
        except Exception as e:
            print(f"获取楼栋电量数据时出错: {e}")
            return jsonify({'error': str(e)}), 500

def start_update_all_buildings_thread():
    """启动更新所有楼栋电量数据的线程"""
    def update_thread():
        print("启动更新所有楼栋电量数据的线程")
        time.sleep(10)  # 等待10秒，确保服务器已完全启动
        
        try:
            # 创建数据目录（如果不存在）
            os.makedirs('data', exist_ok=True)
            
            # 检查上次更新时间
            last_update = None
            if os.path.exists('data/all_buildings_last_update.json'):
                with open('data/all_buildings_last_update.json', 'r') as f:
                    last_update = datetime.fromisoformat(json.load(f)['time'])
            
            current_time = datetime.now()
            
            # 如果是首次更新或距离上次更新超过7天
            if not last_update or (current_time - last_update).days >= 7:
                print("开始更新所有楼栋电量数据...")
                
                # 获取所有楼栋数据
                all_buildings = []
                excluded_buildings = {'一号公寓空调', '七号公寓空调'}
                
                # 读取所有房间数据
                for file_path in glob.glob('data/building_*.json'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        building_data = json.load(f)
                        building_name = building_data['name']
                        if building_name not in excluded_buildings:
                            all_buildings.append({
                                'buildid': building_data['buildid'],
                                'name': building_name,
                                'rooms': building_data['rooms']
                            })
                
                if not all_buildings:
                    print("未找到需要更新的楼栋")
                    return
                
                update_success = True
                
                # 更新每栋楼的数据
                for building in all_buildings:
                    try:
                        print(f"正在更新 {building['name']} 的电量数据...")
                        print(f"房间数量: {len(building['rooms'])}")
                        
                        # 存储该楼的电量数据
                        power_data = []
                        
                        # 直接查询每个房间的电量
                        total_rooms = len(building['rooms'])
                        for index, room in enumerate(building['rooms'], 1):
                            try:
                                room_id = room['id']
                                print(f"[{index}/{total_rooms}] 正在查询 {room['name']} 房间...")
                                res, msg = api.get_power_info(room_id)
                                if not res:
                                    print(f"    [失败] 获取房间 {room_id} 电量失败")
                                    continue
                                    
                                if msg.get('returncode') == '100':
                                    quantity = float(msg['quantity'])
                                    # 检查异常电量
                                    if quantity < 0 or quantity > 300:
                                        print(f"    [异常] {room['name']} 房间电量异常: {quantity}度，已置为0")
                                        quantity = 0  # 将异常值设为0
                                    
                                    power_data.append({
                                        'room_id': room_id,
                                        'room_name': room['name'],
                                        'quantity': str(quantity),  # 转回字符串保持格式一致
                                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    })
                                    print(f"    [成功] {room['name']} 房间电量: {quantity} {msg['quantityunit']}")
                                else:
                                    print(f"    [错误] {room['name']} 房间查询失败: {msg.get('returnmsg', '未知错误')}")
                                
                                time.sleep(4)  # 避免请求过快
                            except Exception as e:
                                print(f"    [错误] 查询房间 {room_id} 时出错: {e}")
                        
                        # 保存电量数据到文件
                        if power_data:
                            power_file = f'data/power_{building["buildid"]}.json'
                            try:
                                with open(power_file, 'w', encoding='utf-8') as f:
                                    json.dump({
                                        'building_name': building['name'],
                                        'building_id': building['buildid'],
                                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                        'rooms': power_data
                                    }, f, indent=4, ensure_ascii=False)
                                print(f"已保存 {building['name']} 的电量数据")
                            except Exception as e:
                                print(f"保存 {building['name']} 电量数据失败: {e}")
                                update_success = False
                        else:
                            print(f"未获取到 {building['name']} 的有效电量数据")
                            update_success = False
                        
                        print(f"完成更新 {building['name']} 的电量数据")
                        
                        # 每栋楼更新完成后，立即更新该楼的更新时间
                        with open(f'data/building_update_{building["buildid"]}.json', 'w') as f:
                            json.dump({'time': datetime.now().isoformat()}, f)
                        
                    except Exception as e:
                        print(f"更新 {building['name']} 数据失败: {e}")
                        update_success = False
                
                # 只有在所有数据都成功更新后才保存总的更新时间
                if update_success:
                    with open('data/all_buildings_last_update.json', 'w') as f:
                        json.dump({'time': current_time.isoformat()}, f)
                    print("所有楼栋电量数据更新完成，已记录更新时间")
                else:
                    print("部分数据更新失败，不记录总的更新时间")
                    
        except Exception as e:
            print(f"更新所有楼栋数据时出错: {e}")
    
    thread = Thread(target=update_thread)
    thread.daemon = True  # 设置为守护线程，主线程结束时会自动结束
    thread.start()

if __name__ == '__main__':
    # 初始化
    api.init()
    web = server()
    
    # 初始化建筑数据（如果需要）
    web.init_building_data()
    web.render()  # 绘制图表
    
    # 启动更新所有楼栋电量数据的线程
    start_update_all_buildings_thread()
    
    # 启动web服务
    app.run(host='0.0.0.0', port=5050)

