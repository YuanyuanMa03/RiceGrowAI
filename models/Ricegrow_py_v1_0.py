################### Imports ########################
import math
import numpy as np
from datetime import datetime,timedelta
import pandas as pd
from pathlib import Path

# ===== 安全的文件读取函数 =====
def safe_read_csv_model(filepath, header=0, sep=",", dtype=None):
    """安全的CSV读取函数，自动检测编码

    Args:
        filepath: 文件路径
        header: 表头行号
        sep: 分隔符
        dtype: 数据类型

    Returns:
        pandas.DataFrame
    """
    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'utf-8-sig', 'latin1']

    for encoding in encodings:
        try:
            return pd.read_csv(filepath, header=header, sep=sep, dtype=dtype, encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception:
            # 如果是其他错误，说明编码可能对了，继续尝试
            continue

    # 如果所有编码都失败，使用默认的 GBK 并让错误抛出
    return safe_read_csv_model(filepath, header=header, sep=sep, dtype=dtype)
################### 生育期(PDT)计算riceDevelopmentModel ########################
def GetLAT(FieldPath):
    Field = pd.read_csv(FieldPath, header=0, sep=",", dtype=str)
    LAT = Field["Latitude"].astype(float).tolist()
    return LAT

def GetSite(FieldPath):
    Field = pd.read_csv(FieldPath, header=0, sep=",", dtype=str)
    Site = Field["site"].tolist() # 地点
    return Site

def GetSowDate(FieldPath):
    Field = pd.read_csv(FieldPath, header=0, sep=",", dtype=str)
    # 提取 "SowingDate" 列，将每个字符串解析为日期对象
    SowDates = [datetime.strptime(date_str, '%Y/%m/%d').date() for date_str in Field["SowingDate"]]
    return SowDates

def GetTransplantDate(FieldPath):
    Field = pd.read_csv(FieldPath, header=0, sep=",", dtype=str)
    # 提取 "SowingDate" 列，将每个字符串解析为日期对象
    TransplantDates = [datetime.strptime(date_str, '%Y/%m/%d').date() for date_str in Field["TransplantDate"]]
    return TransplantDates


def GetCO2(WeatherPath):
    import pandas as pd
    Field = safe_read_csv_model(WeatherPath, header=0, sep=",", dtype=str)

    if len(Field) > 0:
        CO2 = float(Field.loc[0, "CO2"])  # 取第一行的 CO2 值
    else:
        CO2 = 0.0  # 如果文件为空，默认返回 0.0

    return CO2



def GetWeather(WeatherPath,sowDates,Site):
    weather = pd.read_csv(WeatherPath, header=0, sep=",", dtype=str)
    weather['Jour'] = pd.to_datetime(weather['Jour'], format='%Y/%m/%d')
    startDate = pd.to_datetime(sowDates[0])
    endDate = startDate + timedelta(days=365)  # 计算一年后的日期
    weatherDF = weather[
        (weather['Jour'] >= startDate) &
        (weather['Jour'] <= endDate) &
         (weather['Stationno'] == Site[0]) # 确保站点编号一致
        ].sort_values('Jour').reset_index(drop=True)  # 重置索引
    return weatherDF


def GetYear(WeatherPath):

    Field = safe_read_csv_model(WeatherPath, header=0, sep=",", dtype=str)

    if len(Field) > 0:
        date_str = str(Field.loc[0, "Jour"])  # 读取第一行的 jour 值
        year = int(date_str.split("/")[0])  # 按“/”切分，取第一个部分并转成整数
    else:
        year = None  # 如果文件为空，返回 None

    return year



def GetTmax_year(path):
    df = safe_read_csv_model(path)  # 指定编码为 gbk

    if "Tmax" not in df.columns:
        raise ValueError("CSV文件中未找到“日最高温”列")

    return df["Tmax"].to_numpy()

def GetTmin_year(path):
    df = safe_read_csv_model(path)  # 指定编码为 gbk
    if "Tmin" not in df.columns:
        raise ValueError("CSV文件中未找到“日最低温”列")

    return df["Tmin"].to_numpy()

def calc_daily_mean_temp_series(tmax_list, tmin_list):#每日平均气温
    daily_mean_temps = []
    for tmax, tmin in zip(tmax_list, tmin_list):
        mean_temp_day = 0
        for i in range(1, 9):  # I 从 1 到 8
            tfac_i = 0.931 + 0.114 * i - 0.0703 * (i ** 2) + 0.0053 * (i ** 3) 
            temp_i = tmin + tfac_i * (tmax - tmin)
            mean_temp_day += temp_i
        daily_mean_temps.append(mean_temp_day / 8)
    return daily_mean_temps # 每日平均气温

def generate_months_for_whole_year(year):
    from datetime import datetime, timedelta

    months = []
    date = datetime(year, 1, 1)
    while date.year == year:
        months.append(date.month)
        date += timedelta(days=1)

    return months


def accumulate_monthly_temp(daily_mean_temps, months):#每月平均气温
    month_sum_temp = [0.0] * 12
    month_day_counter = [0] * 12

    for mean_temp, month in zip(daily_mean_temps, months):
        idx = month - 1  # 月份从1到12，转为0到11
        month_sum_temp[idx] += mean_temp
        month_day_counter[idx] += 1

    return month_sum_temp, month_day_counter

def calc_year_temp_stats(month_sum_temp, month_day_counter):#年平均气温
    max_month_temp = float('-inf')
    min_month_temp = float('inf')
    year_sum_temp = 0

    month_avg_temp = []
    for i in range(12):
        days = month_day_counter[i] if month_day_counter[i] > 0 else 1
        avg = month_sum_temp[i] / days
        month_avg_temp.append(avg)
        year_sum_temp += avg
        max_month_temp = max(max_month_temp, avg)
        min_month_temp = min(min_month_temp, avg)

    mean_year_temp = year_sum_temp / 12.0
    return month_avg_temp,mean_year_temp,max_month_temp,min_month_temp





def GetTmax(weatherDF):
    Tmax = weatherDF["Tmax"].astype(float).tolist()
    return Tmax

def GetTmin(weatherDF):
    Tmin = weatherDF["Tmin"].astype(float).tolist()
    return Tmin

def CalT24H(Tmax,Tmin): # 24小时平均气温
    T24H = []
    num = len(Tmax)
    for i in range(0,num):
        t24h = (Tmax[i] + Tmin[i]) / 2.0
        T24H.append(t24h)
    return T24H
def GetPrecip(weatherDF):
    Precip = weatherDF["RAIN"].astype(float).tolist()
    return Precip


def GetTheDate(weatherDF):
    TheDate = weatherDF["Jour"].tolist()
    return TheDate

def GetDOY(TheDate):
    DOY = [d.dayofyear for d in TheDate]
    return DOY

def CalLengthTi(Tmax, Tmin):
    LengthTi = []  # 存储每小时的温度
    length = len(Tmax)  # 获取天数
    Tmax = pd.to_numeric(Tmax, errors='coerce')  # 将 Tmax 转换为数值类型
    Tmin = pd.to_numeric(Tmin, errors='coerce')  # 将 Tmin 转换为数值类型
    for i in range(length):  # 遍历每一天的 Tmax 和 Tmin
        for j in range(0, 24):  # 遍历每小时 (1 到 24)
            T = (Tmin[i] + Tmax[i]) / 2.0 + (Tmax[i] - Tmin[i]) / 2.0 * math.cos(
                3.1416 * (j - 14.0) / 12.0)  # 温度日变化余弦曲线，14时为最高温
            # T = round(T, 2)  # 四舍五入到小数点后两位
            LengthTi.append(T)  # 添加到列表中
    return LengthTi # 每小时的温度

def CalTi(LengthTi):
    Ti = []
    LengthTi = pd.to_numeric(LengthTi, errors='coerce')
    n = len(LengthTi) // 24  # 计算天数
    for i in range(n):
        # 每天24个小时，分成一个24小时的数据
        day_temps = LengthTi[i*24:(i+1)*24]
        Ti.append(day_temps)
    return Ti 


def CalDayLong(TheDate, LAT):
    # 存储每个日期的日照时长
    day_lengths = []
    LAT = pd.to_numeric(LAT, errors='coerce')
    # 将纬度转换为弧度
    RAD = math.pi / 180.0
    sin_lat = np.sin(RAD * LAT[0])
    cos_lat = np.cos(RAD * LAT[0])

    for date_str in TheDate:
        # 将日期字符串转换为datetime对象
        #dt = datetime.strptime(date_str, "%Y-%m-%d")
        # 获取该日期是该年的第几天
        DOI = date_str.dayofyear

        # 计算太阳赤纬（Declination）
        declination = -math.asin(math.sin(23.45 * RAD) * math.cos(2.0 * math.pi * (DOI + 10.0) / 365.0))

        # 计算sin和cos值，避免重复计算
        cos_declination = math.cos(declination)

        # 计算日照时间，避免除零错误
        cos_LD = cos_lat * cos_declination
        cos_LD = np.where(cos_LD == 0.0, 0.001, cos_LD)
        sin_LD = sin_lat * math.sin(declination)
        SSCC = sin_LD / cos_LD

        # 计算日照时长
        day_length = 12.0 * (1.0 + 2.0 * np.arcsin(SSCC) / np.pi)
        # 将计算的日照时长添加到列表中
        # day_lengths.append(np.round(day_length, 2))
        day_lengths.append(day_length)

    return day_lengths
################### 计算相对光周期效应RPE ########################
def CalRPE(PS,day_lengths):
    RPE = []
    num = len(day_lengths)
    day_lengths = pd.to_numeric(day_lengths, errors='coerce')
    Pc = round(10.5 + math.pow(1 / PS, 0.5), 4)
    for i in range(0,num):
        if day_lengths[i] < 10.5:
            dayRPE = 1.0
        elif 10.5 < day_lengths[i] <= Pc:
            tempDL = day_lengths[i] - 10.5
            dayRPE = 1.0 - PS * math.pow(tempDL, 2)
        else:
            dayRPE = 0
        RPE.append(dayRPE)
    return RPE,Pc
################### PDT ########################
def CalPDT(plantingDepth,RPE,FDF,Ti,TS,TO,IE,HF,SowDates,TransplantDates):
    RPE = pd.to_numeric(RPE, errors='coerce')
    Ti = pd.to_numeric(Ti, errors='coerce')

#################### 计算移栽日期与播种日期之间的天数差 ####################
    SowD = SowDates[0]
    traD = TransplantDates[0]
    transplantDays = (traD - SowD).days
    isRejuvenationPeriod = False  # 是否为返青期
    isEmergence = False  # 是否为出苗期
#################### 开花后第1天到第i天的高温度日积累 ####################
    DHDD = 0
#################### 粳稻与籼稻开花至成熟所需要的生长度日 ####################
    JGDDAM = 620
    XGDDAM = 520
    b = 0.0
#################### DPE ####################
    # DPE = np.zeros((1,), dtype=np.float64)
    DPE = 0.0
    DTTS = 0.0
    DPEList = []
#################### 出苗期GDD ####################

    EMGDD = 45.0 + 7.0 * plantingDepth
    # EMGDD = 66
#################### GDD ####################
    GDDList = []
    GDD = 0.0
    TrplShockGDD = 0.0
    TrplGDD = 0.0
    #TempSumDTT = np.zeros((1,), dtype=np.float64)
    TempSumDTT = 0.0
    DTTList = []
    DTT = 0.0
    DTTSList =[]
    TTS = 0.0  # 当日累积热时间
    TTSList = []
#################### PDT ####################
    # tempPDT = np.zeros((1,), dtype=np.float64)
    tempPDT = 0.0
    PDT = []
########################################
    num = len(RPE)
    for i in range(0,num):
#################### DTE ####################
        RTEI = 0.0
       # SumTE_i = np.zeros((1,), dtype=np.float64)
        SumTE_i = 0.0
        DTTS24Sum = 0.0
        TempSumDTT = 0.0
########################################## Tb,Tm与温度阈值初始化 ##########################################
        Tb = 10.0
        Tm = 42.0
        Th = 35  # 开花期后高温阈值
        Tc = 18.5 #开花期低温阈值
        Tgf = 28.5  # 灌浆阈值 sph, sunting
        Tcgf = 20  # 灌浆期低温阈值 kang
########################################## 高温与低温度日初始化 ##########################################
        hHDD = 0#开花后期的每小时高温温度积累值
        hHDD0 = 0#孕穗期的每小时高温温度积累值
        hGFHDD = 0#灌浆期每小时高温温度积累值
        hCDD = 0#开花后期的每小时低温温度积累值
        hGFCDD = 0#灌浆期每小时低温温度积累值
        HDDsum = 0#开花期到成熟期的每天高温积累总量
        GFHDDsum = 0#灌浆期到成熟期的每天高温积累总量
        GFCDDsum = 0#灌浆期到成熟期的每天低温积累总量
        CDDsum = 0#开花期到成熟期的每天低温积累总量
        dHDD = 0#计算开花期到成熟期的每天高温度日
########################################## 具体年月日 ##########################################
        thedate = SowD+timedelta(days=i)
########################################## 计算返青期GDD ##########################################
        if i == transplantDays   :  # 移栽
            TrplGDD = GDD
            TrplShockGDD = TrplGDD + TrplGDD * 0.15
            isRejuvenationPeriod = True  # 移栽后进入返青期
##########################################
        dayT24 = Ti[i]
        for j in range(0,24):
########################################## 高温胁迫与低温胁迫 ##########################################
            if tempPDT >= 38:  # 籽粒灌浆某阶段
                if dayT24[j] < Tgf:
                    hGFHDD = 0
                else:
                    hGFHDD = dayT24[j] - Tgf

                if dayT24[j] < Tcgf:
                    hGFCDD = 0
                else:
                    hGFCDD = dayT24[j] - Tcgf

            elif tempPDT < 32 and tempPDT >= 18:  # 穗形成阶段
                if dayT24[j] < 33:
                    hHDD0 = 0
                else:
                    hHDD0 = dayT24[j] - 33

            elif tempPDT >= 32:  # 其他阶段
                if dayT24[j] < Th:
                    hHDD = 0
                else:
                    hHDD = dayT24[j] - Th

                if dayT24[j] > Tc:
                    hCDD = 0
                else:
                    hCDD = Tc - dayT24[j]
            HDDsum = np.round(HDDsum + hHDD, 4)
            CDDsum = CDDsum + hCDD
            GFHDDsum = GFHDDsum + hGFHDD
            GFCDDsum = GFCDDsum + hGFCDD
########################################## RTE ##########################################
            if not isRejuvenationPeriod:
                if tempPDT < 18:
                    if Tb <= dayT24[j] <= Tm:#出苗至拔节
                        tempB = (Tm - TO) / (TO - Tb)
                        tempA = ((dayT24[j] - Tb) / (TO - Tb)) * math.pow(((Tm - dayT24[j]) / (Tm - TO)), tempB)
                        RTEI = math.pow(tempA, TS)
                    # elif dayT24[j] <= Tb:
                    #     RTEI = 0.0
                elif 18 <= tempPDT <= 32:#穗形成阶段
                    if Tb <= dayT24[j] < Tm:
                        tempB = np.round((Tm - TO) / (TO - Tb), 4)
                        tempA = np.round(
                            ((dayT24[j] - Tb) / (TO - Tb)) * math.pow(((Tm - dayT24[j]) / (Tm - TO)), tempB), 4)
                        RTEI = np.round(math.pow(tempA, TS), 4)
                    # elif dayT24[j] >= TO:
                    #     tempB = np.round((Tm - TO) / (TO - Tb), 4)
                    #     tempA = np.round(
                    #         (((2 * TO - dayT24[j]) - Tb) / (TO - Tb)) * math.pow(((Tm - (2 * TO - dayT24[j])) / (Tm - TO)),
                    #                                                            tempB), 4)
                    #     RTEI = np.round(math.pow(tempA, TS), 4)
                    # else:
                    #     RTEI = 0.0
                elif 32 < tempPDT <= 57:#开花至成熟阶段
                    if Tb <= dayT24[j] < Tm:
                        tempB = np.round((Tm - TO) / (TO - Tb), 4)
                        tempA = np.round(
                            ((dayT24[j] - Tb) / (TO - Tb)) * math.pow(((Tm - dayT24[j]) / (Tm - TO)), tempB), 4)
                        RTEI = np.round(math.pow(tempA, TS), 4)
                    # elif TO <= dayT24[j] <= 35:
                    #     RTEI = 1.0
                    # else:
                    #     RTEI = 0.0
                SumTE_i = SumTE_i + RTEI
                DTTS24Sum =DTTS24Sum + dayT24[j] * RTEI
########################################## GDD ##########################################
            TempSumDTT = TempSumDTT + (dayT24[j] - Tb)
########################################## 计算开花期到成熟期的每天高温度日 ##########################################
        dHDD = round(HDDsum / 24, 4)
        DHDD = DHDD + dHDD #开花后第1天到第i天的高温度日
        DTEHS = round(DHDD / (HF * JGDDAM), 4)
        DTT = TempSumDTT / 24.0

########################################## GDD ##########################################
        GDD = GDD + TempSumDTT / 24.0 ###################修改
########################################## 出苗期判断 ##########################################
        if not isEmergence and GDD >= EMGDD:
            isEmergence = True
########################################## 返青期判断 ##########################################
        if isRejuvenationPeriod and GDD >= TrplShockGDD:
            isRejuvenationPeriod = False
##########################################计算PDT##########################################
        if isEmergence and not isRejuvenationPeriod:
###################### DTE #########################
            DTE = SumTE_i / 24.0 + DTEHS
            # DTE = SumTE_i / 24.0
####################################################
            if tempPDT < 8:
                DPE = DTE * IE
            elif tempPDT < 18:
                DPE = DTE * RPE[i]
            elif tempPDT < 32:
                DPE = DTE
            elif tempPDT < 57:
                DPE = DTE * FDF
            tempPDT = tempPDT + DPE
            DTTS = DTTS24Sum / 24.0  # 每日热累积时间
            TTS = TTS + DTTS
        a = tempPDT
        if a > 57:
            b = b + 1
        if b >= 2:
            a = 58
        PDT.append(a)
        GDDList.append(GDD)
        TTSList.append(TTS)
        DPEList.append(DPE)
        DTTSList.append(DTTS)
        DTTList.append(DTT)
    return PDT,GDDList,EMGDD,TrplShockGDD,TTSList,DPEList,TrplGDD,DTTSList,DTTList

######################## 地上部分配指数PIS----RiceTopRootModel--- ########################----2024/11/29已检验
def CalPIS(PDT):
    PIS = []
    num = len(PDT)
    for i in range(0,num):
        tempPIS = -8.42 * 0.00001 * PDT[i] * PDT[i] + 0.01 * PDT[i] + 0.63
        PIS.append(tempPIS)
    return PIS
######################## 绿叶分配指数PILVG----RiceTopRootModel----P59 ########################----2024/11/30已检验
def CalPILVG(PDT):
    PILVG = []
    tempPILVG = 0.0
    num = len(PDT)
    for i in range(0,num):
        if PDT[i] < 26:
            tempPILVG =0.54 - 0.0046 * PDT[i]
            if tempPILVG < 0:
                tempPILVG = 0.01
        elif PDT[i] >= 26:
            tempPILVG = 1.4532 * math.exp(-0.0492 * PDT[i])
            # tempPILVG = 1.3607 * math.exp(-0.043 * PDT[i])
            #tempPILVG = 1.3607 * math.exp(-0.043 * PDT[i])#######
            # tempPILVG = 1.4532 * math.exp(-0.0422 * PDT[i])########
            # tempPILVG = 1.3607 * math.exp(-0.043 * PDT[i])
        PILVG.append(tempPILVG)
    return PILVG
######################## 穗部分配指数PISP----RiceTopRootModel----P64 ########################----2024/11/30已检验
def CalPISP(PDT,PHI):
    PISP = []
    tempPISP = 0.0
    PPIP = PHI / 0.87 #潜在穗分配指数
    num = len(PDT)
    for i in range(0,num):
        if PDT[i] < 24:
            tempPISP = 0
        else:
            tempPISP = PPIP / (1 + math.exp(-0.2804 * (PDT[i] - 39)))
            #tempPISP = PPIP / (1 + math.exp(-0.1613 * (PDT[i] - 45)))
        PISP.append(tempPISP)
    return PISP
######################## 比叶面积SLA----RiceTopRootModel----P86 ########################----2024/11/30已检验
def CalSLA(GDD,SLAc):
    SLA = []
    daySLA = 0.0
    num = len(GDD)
    for i in range(0,num):
        if GDD[i] <= 1200:
            daySLA = (SLAc / 200) * (0.0002 * GDD[i]**2 - 0.5604 * GDD[i] + 581.0432)
        else:
            daySLA = SLAc
        SLA.append(daySLA)
    return SLA
################### 生理年龄对光合作用最大速率的影响因子FA----RicePhotoBiomassModel----P98 ########################----2024/11/30已检验
def CalFA(PDT,PF):
    FA = []
    num = len(PDT)
    tempFA = 0.0
    for i in range(0,num):
        if PDT[i] < 28:
            tempFA = 1.0
        else:
            tempFA = math.exp(-PF * (PDT[i] - 28))
        FA.append(tempFA)
    return FA
#################### 日均温对最大光合作用速率的影响因子FTMP----RicePhotoBiomassModel----P79 #######################----2024/11/30已检验
def CalFTMP(T24H):
    FTMP = []
    Tb = 10.0 #基点温度
    Tol = 24.0 #最适温度下限值
    Tou = 34.0 #最适温度上限值
    Tmax = 45.0 #最高温度
    tempFTMP = 0.0
    num = len(T24H)
    for i in range(0,num):
        if Tb <= T24H[i] < Tol:
            tempFTMP = math.sin(((T24H[i] - Tb) / (Tol - Tb)) * math.pi / 2)
        elif Tol <= T24H[i] < Tou:
            tempFTMP = 1.0
        elif Tou <= T24H[i] < Tmax:
            tempFTMP = math.cos(((T24H[i] - Tou) / (Tmax - Tou)) * math.pi / 2)
        else:
            tempFTMP = 0.00001
        FTMP.append(tempFTMP)
    return FTMP
#################### 二氧化碳影响因子FCO2----RicePhotoBiomassModel----P106 ########################----
def CalFCO2(Cx):
    tempCx = Cx / 340.0
    FCO2 = 1.0 + 0.80 * math.log(tempCx, 10)
    return FCO2
######################## 单叶最大光合作用速率(饱和光强时的光合作用速率计算)AMAX----RicePhotoBiomassModel----P110 ########################----2024/12/3已检验
def CalAMAX(FTMP,FA,FCO2,AMX):
    AMAX = []
    num = len(FTMP)
    for i in range(0,num):
        tempAMAX = AMX * FTMP[i] * FA[i] * FCO2#####################存在问题:AMAX = AMX * FT * FDVS * FCO2 * Math.Min(FW,FN);
        AMAX.append(tempAMAX)
    return AMAX
######################## 日偏差DEC----RicePhotoBiomassModel----P61 ########################----
def CalDEC(DOY):
    DEC = []
    for doy in DOY:
        sin = math.sin(23.45 * math.pi / 180)
        cos = math.cos(2.0 * math.pi * (doy + 10.0) / 365.0)
        SC = sin * cos
        tempDEC = -math.asin(SC)
        DEC.append(tempDEC)
    return DEC
######################## 中间变量SSIN----RicePhotoBiomassModel----P62 ########################
def CalSSIN(LAT,DEC):
    SSIN = []
    num = len(DEC)
    for i in range(0,num):
        tempSSIN = math.sin(LAT[0] * math.pi / 180) * math.sin(DEC[i])
        SSIN.append(tempSSIN)
    return SSIN
######################## 中间变量CCOS----RicePhotoBiomassModel----P63 ########################
def CalCCOS(LAT,DEC):
    CCOS = []
    num = len(DEC)
    for i in range(0,num):
        tempCCOS = math.cos(LAT[0] * math.pi / 180) * math.cos(DEC[i])
        CCOS.append(tempCCOS)
    return CCOS
################### 中间变量SSCC----RicePhotoBiomassModel----P64 #############
def CalSSCC(SSIN,CCOS):
    SSCC = []
    num = len(SSIN)
    for i in range(0,num):
        tempSSCC = SSIN[i] / CCOS[i] #中间变量
        SSCC.append(tempSSCC)
    return SSCC
############### 每日太阳有效高度DSINBE----RicePhotoBiomassModel----P69 ########################
def CalDSINBE(Day_lengths,SSIN,CCOS,SSCC):
    DSINBE = []
    num = len(Day_lengths)
    for i in range(0,num):
        DSINBE_1 = SSIN[i] + 0.4 * (math.pow(SSIN[i], 2) + math.pow(CCOS[i], 2) * 0.5)
        DSINBE_2 = CCOS[i] * (2 + 3 * 0.4 * SSIN[i]) * math.sqrt(1 - math.pow(SSCC[i], 2)) / math.pi
        tempDSINBE = 3600.0 * (Day_lengths[i] * DSINBE_1 + 12 * DSINBE_2)
        DSINBE.append(tempDSINBE)
    return DSINBE
######################## 太阳时间Th_jSeq----RicePhotoBiomassModel----P128 ########################----2024/12/3已检验
def CalLengthTh_j(Day_lengths):
    LengthTh_j = []
    DIS3 = [0.112702, 0.5, 0.887298] #3点法
    num = len(Day_lengths)
    for i in range(0,num):
        for j in range(0,3):
            tempTh_j = 12 + 0.5 * Day_lengths[i] * DIS3[j] #太阳时间
            LengthTh_j.append(tempTh_j)
    return LengthTh_j

def CalTh_j(LengthTh_j):
    Th_j = []
    ls_len = len(LengthTh_j)
    n = ls_len // 3  # 使用整除来确保n是整数
    j = ls_len // n
    k = ls_len % n
    for t in range(0,(n - 1) * j,j):
        Th_j.append(LengthTh_j[t:t + j])
    Th_j.append(LengthTh_j[(n - 1) * j:])
    return Th_j
######################## 第i天第j个时刻太阳高度角正弦值SINB_ij----RicePhotoBiomassModel----P131 ########################----2024/12/3已检验
def CalLengthSINB_ij(SSIN,CCOS,Th_j):
    LengthSINB_ij = []
    num = len(SSIN)
    for i in range(0,num):
        for j in range(0,3):
            SINB_ij = SSIN[i] + CCOS[i] * math.cos(2 * math.pi * (Th_j[i][j] + 12) / 24) #第i天第j个时刻太阳高度角正弦值
            if SINB_ij < 0.0:
                SINB_ij = 0.0
            LengthSINB_ij.append(SINB_ij)
    return LengthSINB_ij
def CalSINB_ij(LengthSINB_ij):
    SINB_ij = []
    ls_len = len(LengthSINB_ij)
    n = ls_len // 3  # 使用整除来确保n是整数
    j = ls_len // n
    k = ls_len % n
    for t in range(0,(n - 1) * j,j):
        SINB_ij.append(LengthSINB_ij[t:t + j])
    SINB_ij.append(LengthSINB_ij[(n - 1) * j:])
    return SINB_ij
################### 读取太阳总辐射solarRadiation ########################
def GetdSunH(weatherDF):
    dSunH = weatherDF["SRAD"].astype(float).tolist()
    return dSunH
################### 计算太阳总辐射solarRadiation ########################
# def CalQ(DL,dSunH,SSIN,CCOS,SSCC,DOY):
#     Q = []
#     num = len(DL)
#     for i in range(0, num):
#         dDSINB = 3600.0 * (DL[i] * SSIN[i] + 24.0 * CCOS[i] * math.sqrt(1.0 - SSCC[i] * SSCC[i]) / math.pi)
#         SC = 1370.0 * (1.0 + 0.033 * math.cos(2.0 * math.pi * DOY[i] / 365.0))
#         DSO = SC * dDSINB
#         tempQ = DSO * (0.25 + 0.45 * dSunH[i] / DL[i])
#
#         Q.append(tempQ)
#     return Q
def CalQ(weatherDF):
    Q = weatherDF["SRAD"].astype(float).tolist()
    Q = [q * 1000000 for q in Q]
    return Q

######################## 光合有效辐射PAR_i----RicePhotoBiomassModel----P133 ########################----2024/12/3已检验
def CalLengthPAR_i(Q,SINB_ij,DSINBE):
    LengthPAR_i = []
    num = len(Q)
    for i in range(0,num):
        for j in range(0,3):
            tempPAR_i = 0.5 * Q[i] * SINB_ij[i][j] * (1.0 + 0.4 * SINB_ij[i][j]) / DSINBE[i]
            LengthPAR_i.append(tempPAR_i)
    return LengthPAR_i
def CalPAR_i(LengthPAR_i):
    PAR_i = []
    ls_len = len(LengthPAR_i)
    n = ls_len // 3  # 使用整除来确保n是整数
    j = ls_len // n
    k = ls_len % n
    for t in range(0,(n - 1) * j,j):
        PAR_i.append(LengthPAR_i[t:t + j])
    PAR_i.append(LengthPAR_i[(n - 1) * j:])
    return PAR_i
######################## 第j个时刻冠层消光系数K_j----RicePhotoBiomassModel----P140 ########################----2024/12/3已检验
def CalLengthK_j(SINB_ij,KF,PDT):
    LengthK_j = []
    num = len(SINB_ij)
    for i in range(0,num):
        for j in range(0,3):
            tempK_j = KF * PDT[i] + 0.2222
            LengthK_j.append(tempK_j)
    return LengthK_j
def CalK_j(LengthK_j):
    K_j = []
    ls_len = len(LengthK_j)
    n = ls_len // 3  # 使用整除来确保n是整数
    j = ls_len // n
    k = ls_len % n
    for t in range(0,(n - 1) * j,j):
        K_j.append(LengthK_j[t:t + j])
    K_j.append(LengthK_j[(n - 1) * j:])
    return K_j
######################## 第j个时刻冠层对光的反射率p_j----RicePhotoBiomassModel----P143 ########################----2024/12/3已检验
def CalLengthp_j(SINB_ij):
    o = 0.2 #单叶散射系数
    Lengthp_j = []
    num = len(SINB_ij)
    for i in range(0,num):
        for j in range(0,3):
            tempp_j = ((1 - math.sqrt(1 - o)) / (1 + math.sqrt(1 - o))) * (2.0 / (1 + 2 * SINB_ij[i][j]))
            Lengthp_j.append(tempp_j)
    return Lengthp_j
def Calp_j(Lengthp_j):
    p_j = []
    ls_len = len(Lengthp_j)
    n = ls_len // 3  # 使用整除来确保n是整数
    j = ls_len // n
    k = ls_len % n
    for t in range(0,(n - 1) * j,j):
        p_j.append(Lengthp_j[t:t + j])
    p_j.append(Lengthp_j[(n - 1) * j:])
    return p_j

######################## FertilizerLength----RiceNBalanceModel----P89 ########################----
def ReadFertilizerData(FertilizerPath):
    # 读取数据
    df = safe_read_csv_model(FertilizerPath, header=0)

    # 提取两列并转为数值型
    DOY_list = pd.to_numeric(df["DOY"], errors="coerce").astype("Int64").tolist()
    Fertilizer_list = pd.to_numeric(df["UREAAmount"], errors="coerce").astype(float).tolist()

    return DOY_list, Fertilizer_list

def GetUREA(DOY, DOY_list, Fertilizer_list):
    UREA = []
    for doy in DOY:
        if doy in DOY_list:  # 判断该天是否在施肥表里
            idx = DOY_list.index(doy)  # 找到索引
            tempUREA = Fertilizer_list[idx]
        else:
            tempUREA = 0.0
        UREA.append(tempUREA)
    return UREA
###### 土层容重 dBD ########################
def GetdBD(SoilFieldPath):
    Field = safe_read_csv_model(SoilFieldPath, header=0, sep=",", dtype=str)
    dBD = Field["bulkWeight"].astype(float).tolist()
    if len(dBD) >= 2:
        dBD = dBD[:2] + [dBD[1]] * (10 - 2)
    return dBD
################### 土层饱和含水量---RiceWBalanceModel----P256 ########################
def Calsat(dBD):#土壤容重
    sat = []
    for l in range(0,10):
        tempsat = math.fabs(1 - dBD[l] / 2.65)
        sat.append(tempsat)
    return sat
######################## 田间持水量dul ########################
def GetDUL(SoilFieldPath):
    Field = safe_read_csv_model(SoilFieldPath, header=0, sep=",", dtype=str)
    dul = Field["fieldCapacity"].astype(float).tolist()
    if len(dul) >= 2:
        dul = dul[:2] + [dul[1]] * (10 - 2)
    return dul
################### 土层饱和导水率----RiceWBalanceModel----P256 ########################
def CalKSat(sat,dul):
    KSat = []
    for l in range(0,10):
        tempKSat = 75.0 * math.pow((sat[l] - dul[l]) / dul[l], 2)
        KSat.append(tempKSat)
    return KSat
################### Kt----RiceWBalanceModel----P256 ###################----
def CalKt(Tmax):
    Kt = []
    tempKt = 0.0
    num = len(Tmax)
    for i in range(0,num):
        if Tmax[i] < 5:
            tempKt = 0.01 * math.exp(0.18 * (Tmax[i] + 20))
        elif Tmax[i] >= 35:
            tempKt = 0.05 * (Tmax[i] - 35) + 1.1
        else:
            tempKt = 1.1
        a = tempKt + 0
        Kt.append(a)
    return Kt
################### 土壤条件对径流影响WF----RiceWBalanceModel----P1125 ###################----
def CalWF(Layer):
    tempDepth = 0.0  # 初始化累计深度
    xx = 0.0  # 初始化xx
    tempWF = 0.0
    WF = []
    for l in range(0,10):
        tempDepth = tempDepth +Layer[l]  # 累加土层深度
        wx = 1.016 * (1 - math.exp(-4.16 * tempDepth / 40))  # 计算 wx
        tempWF = wx - xx  # 计算临时 WF
        xx = wx  # 更新 xx
        WF.append(tempWF)  # 记录当前层的 WF
    return WF
# ######################## 凌晨临界叶水势LwpCr---RiceWBalanceModel----P1041 ########################----
# def CalLwpCr(PDT):
#     LwpCr = []
#     tempLwpCr = 0.0
#     num = len(PDT)
#     for i in range(0,num):
#         if PDT[i] < 16.1:
#             tempLwpCr = -10.0
#         elif 16.1 <= PDT[i] < 21.4:
#             tempLwpCr = -8.0
#         elif 21.4 <= PDT[i] < 31:
#             tempLwpCr = -9.0
#         else:
#             tempLwpCr= -12.0
#         a = tempLwpCr + 0
#         LwpCr.append(a)
#     return LwpCr
################## 每层土壤铵态氮含量 ########################-
def GetNH4(SoilFieldPath):
    Field = safe_read_csv_model(SoilFieldPath, header=0, sep=",", dtype=str)
    dNH40 = Field["ammoniaNitrogen"].astype(float).tolist()
    return dNH40
def CaldNH4(dNH40):
    dNH4 = dNH40[:2].copy()  # 使用copy避免修改原列表
    # 后8层使用第一层值的30%
    tempdNH4 = dNH40[0] * 0.3
    dNH4.extend([tempdNH4] * 8)
    return dNH4
################### 每层土壤硝态氮含量 ########################--
def GetdNO3(SoilFieldPath):
    Field = safe_read_csv_model(SoilFieldPath, header=0, sep=",", dtype=str)
    dNO30 = Field["nitrateNitrogen"].astype(float).tolist()
    return dNO30
def CaldNO3(dNO30):#35
    dNO3 = dNO30[:2].copy()  # 使用copy避免修改原列表
    # 后8层使用第一层值的30%
    tempdNO3 = dNO30[0] * 0.3
    dNO3.extend([tempdNO3] * 8)
    return dNO3
################### 每层全氮含量  ########################--
def GetdTN(SoilFieldPath):
    Field = safe_read_csv_model(SoilFieldPath, header=0, sep=",", dtype=str)
    dTN0 = Field["totaNitrogen"].astype(float).tolist()
    return dTN0
def CaldTN(dTN0):#0.95
    dTN = dTN0[:2].copy()  # 使用copy避免修改原列表
    # 后8层使用第一层值的30%
    tempdTN = dTN0[0] * 0.3
    dTN.extend([tempdTN] * 8)
    return dTN
################### 有机质含量 ########################
def Getm_inputOM(SoilFieldPath):
    Field = safe_read_csv_model(SoilFieldPath, header=0, sep=",", dtype=str)
    m_inputOM0 = Field["organicMatter"].astype(float).tolist()
    return m_inputOM0
def Calm_inputOM(m_inputOM0):#13.3
    m_inputOM = m_inputOM0[:2].copy()  # 使用copy避免修改原列表
    # 后8层使用第一层值的30%
    tempm_inputOM = m_inputOM0[0] * 0.3
    m_inputOM.extend([tempm_inputOM] * 8)
    return m_inputOM 
################### 黏粒含量 ########################
def GetdClay(SoilFieldPath):
    Field = safe_read_csv_model(SoilFieldPath, header=0, sep=",", dtype=str)
    dClay = Field["clayParticle"].astype(float).tolist()
    if len(dClay) >= 2:
        dClay = dClay[:2] + [dClay[1]] * (10 - 2)
    return dClay
# ################### m_inputNKHS ########################
# def Calm_inputNKHS(dTN,m_inputOM,dClay):
#     m_inputNKHS = []
#     for l in range(0,10):
#         tempm_inputNKHS = 0.186 * (dTN[l] + m_inputOM[l] * 0.055) * (1 - 0.356 * dClay[l]) * 1000
#         m_inputNKHS.append(tempm_inputNKHS)
#     return m_inputNKHS
######################## m_ntFPH ########################
def GetdPH(SoilFieldPath):
    Field = safe_read_csv_model(SoilFieldPath, header=0, sep=",", dtype=str)
    dPH = Field["pH"].astype(float).tolist()
    if len(dPH) >= 2:
        dPH = dPH[:2] + [dPH[1]] * (10 - 2)
    return dPH
def Calm_ntFPH(dPH):
    m_ntFPH = []
    tempm_ntFPH = 0.0
    for l in range(0,10):
        if dPH[l] < 6:
            tempm_ntFPH = (dPH[l] - 4.5) / 1.5
        elif dPH[l] > 8:
            tempm_ntFPH = 9 - dPH[l]
        elif dPH[l] < 0:
            tempm_ntFPH = 0.0
        else:
            tempm_ntFPH = 1.0
        a = tempm_ntFPH + 0
        m_ntFPH.append(a)
    return m_ntFPH
######################## 计算日均温 ########################---
def CaldTmean(Tmax,Tmin):
    dTmean = []
    num = len(Tmax)
    for i in range(0,num):
        dT = 0.5 * Tmax[i] + 0.5 * Tmin[i]
        dTmean.append(dT)
    return dTmean
######################## 叶片临界含N率（KgN/Kg)NCLVC---RiceNBalanceModel---
def CalNCLVC(PDT):
    NCLVC = []
    num = len(PDT)
    for i in range(0,num):
        dayTNCLVC = -0.000008 * PDT[i] * PDT[i] + 0.0002 * PDT[i] + 0.0374
        NCLVC.append(dayTNCLVC)
    return NCLVC
######################## 临界氮浓度TCNC----RicetNBalanceModel----
def CalTCNC(NCLVC):
    return [x * 0.75 for x in NCLVC]
######################## 根临界含N率NCRTC---RiceNBalanceModel---
def CalNCRTC(PDT,NCLVC):
    NCRTC = []
    dayNCRTC = []
    num = len(PDT)
    for i in range(0,num):
        if PDT[i] > 25:
            dayNCRTC = 0.0118 - (0.0118 - 0.009) * (PDT[i] - 25) / (57 - 25)
        else:
            dayNCRTC = 0.35 * NCLVC[i]
        a = dayNCRTC + 0
        NCRTC.append(a)
    return NCRTC
######################## 植株最小含N率LNCL----RiceNBalanceModel----P564 ########################
def CalTNCL(TCNC):
    return [x * 0.5 for x in TCNC]
######################## 最大N浓度TNMAX----RiceNBalanceModel----P576 ########################
def CalTNMAX(TCNC):
    TNMAX = []
    num = len(TCNC)
    for i in range(0,num):
        dayTNMAX = 1.05 * TCNC[i]
        TNMAX.append(dayTNMAX)
    return TNMAX
######################## 根系偏好因子WR----RiceWBalanceModel---
def CalWR(Layer):#(土层数量，土层厚度)
    WR = []
    WSUM = 0.0
    TempLayersDepth = 0.0 #土壤深度
    for j in range(0,10):
        z = TempLayersDepth + Layer[j] / 2.0
        tempWR = math.exp(-3.0 * z / 150)
        TempLayersDepth = TempLayersDepth + Layer[j]
        WSUM = WSUM + tempWR
        WR.append(tempWR)
    return WR,WSUM
########################秸秆残茬初始化#################
def CalWS(ResidueDepth, Layer):
    WS = [0.0] * 10  # 初始化10个0
    tempDepth = Layer[0]
    WS[0] = tempDepth / ResidueDepth
    for l in range(1, len(Layer)):
        tempDepth += Layer[l]
        if tempDepth <= ResidueDepth:
            WS[l] = Layer[l] / ResidueDepth
        else:
            WS[l] = (ResidueDepth - (tempDepth - Layer[l])) / ResidueDepth
            break
    return WS
######################## 地表五日连续平均温度 #######################
def CalFiveDayAveST(Tmax,Tmin):
    FiveDayAveST = []
    for i in range(0,5):
        FiveDayAveST.append(0.6 * Tmax[0] + 0.4 * Tmin[0])
    return FiveDayAveST
######################## 地表五日连续累计温度 ########################-
def CalaccumSoilT(dTmean):
    accumSoilT = dTmean[0] * 5 #地表五日累计温度
    return accumSoilT
######################## 土层容重平均值 dBD ########################
def CalAvedBD(dBD):
    sumdBD = 0
    for l in range(0,10):
        sumdBD = sumdBD + dBD[l]
    AvedBD = sumdBD / 10
    return AvedBD
######################## 土层实际含水量sw ########################
def Getsw(SoilFieldPath):
    Field = safe_read_csv_model(SoilFieldPath, header=0, sep=",", dtype=str)
    sw = Field["actualWater"].astype(float).tolist()
    if len(sw) >= 2:
        sw = sw[:2] + [sw[1]] * (10 - 2)
    return sw
######################## 萎蔫含水量ll ########################
def Getll(SoilFieldPath):
    Field = safe_read_csv_model(SoilFieldPath, header=0, sep=",", dtype=str)
    ll = Field["wiltingPoint"].astype(float).tolist()
    if len(ll) >= 2:
        ll = ll[:2] + [ll[1]] * (10 - 2)
    return ll
######################## 秸秆量 ########################
def GetpreviousCropStraw(ResiduePath):
    Field = safe_read_csv_model(ResiduePath, header=0, sep=",", dtype=str)
    previousCropStraw = float(Field.loc[0, "previousCropStraw"])
    return previousCropStraw

def GetpreviousCropStubble(ResiduePath):
    Field = safe_read_csv_model(ResiduePath, header=0, sep=",", dtype=str)
    previousCropStubble = float(Field.loc[0, "previousCropStubble"])
    return previousCropStubble

def GetresidueDepth(ResiduePath):
    Field = safe_read_csv_model(ResiduePath, header=0, sep=",", dtype=str)
    residueDepth = float(Field.loc[0, "residueDepth"])
    return residueDepth
######################## 管理数据 ########################
def GetPlantSeedQuantity(PlantingPath):
    Field = safe_read_csv_model(PlantingPath, header=0, sep=",", dtype=str)

    if len(Field) > 0:
        ABIOMASS = float(Field.loc[0, "plantSeedQuantity"])
        plantingDepth = float(Field.loc[0, "plantingDepth"])


    return ABIOMASS,plantingDepth
######################## 秧苗比例 Diluted ########################
def GetDiluted(PlantingPath,ABIOMASS,TGW):
    Field = safe_read_csv_model(PlantingPath, header=0, sep=",", dtype=str)
    numberPerHill = float(Field.loc[0, "numberPerHill"])
    numberHillsM2 = float(Field.loc[0, "numberHillsM2"])
    PLANTS = (1000*1000*ABIOMASS)/(10000*TGW)
    Diluted = PLANTS / (numberPerHill*numberHillsM2)
    return Diluted


######################## 品种参数 ########################
def GetCultivarParams(CultivarPath):
    Field = safe_read_csv_model(CultivarPath, header=0, sep=",", dtype=str)

    # 读取品种名称
    PZ = str(Field.at[0, "PZ"])
    
    # 依次读取第一行的值，并转换为 float
    PS  = float(Field.at[0, "PS"])
    TS  = float(Field.at[0, "TS"])
    TO  = float(Field.at[0, "TO"])
    IE  = float(Field.at[0, "IE"])
    HF  = float(Field.at[0, "HF"])
    FDF = float(Field.at[0, "FDF"])
    PHI = float(Field.at[0, "PHI"])
    SLAc= float(Field.at[0, "SLAc"])
    PF  = float(Field.at[0, "PF"])
    AMX = float(Field.at[0, "AMX"])
    KF  = float(Field.at[0, "KF"])
    TGW = float(Field.at[0, "TGW"])
    RGC = float(Field.at[0, "RGC"])
    LRS = float(Field.at[0, "LRS"])
    TLN = float(Field.at[0, "TLN"])
    EIN = float(Field.at[0, "EIN"])
    TA  = float(Field.at[0, "TA"])
    SGP = float(Field.at[0, "SGP"])
    PC  = float(Field.at[0, "PC"])
    RAR = float(Field.at[0, "RAR"])

    return PZ, PS, TS, TO, IE, HF, FDF, PHI, SLAc, PF, AMX, KF, TGW, RGC, LRS, TLN, EIN, TA, SGP, PC, RAR

######################## 实际生物量ABIOMASS ########################
def RiceGrowModel(DTTList,TNCL,NCRTC,TCNC,NCLVC,dTotAN,dPH,m_ntFPH,m_inputOM,HUM,NHUM,FOMpool,WSUM,WR,WS,m_dStubble,m_dStraw,FOM,FON,dUreaOut,dUreaUp,dNH4out,dNH4up,dNO3up,dNO3out,dBD,No3,NH4,Urea,UREA,MinMonthTemp,MaxMonthTemp,MeanYearTemp,FiveDayAveST,accumSoilT,DOY,AvedBD,KSat,Layer,sat,dul,ll,sw0,Kt,dTmean,Q,dRLV,Precip,DL,PDT,TTSlist,DPElist,DTTSlist,ABIOMASS,TGW,p_j,PAR_i,K_j,AMAX,RGC,T24H,PIS,PILVG,PISP,Tmax,Tmin,LRS,TLN,EIN,TA,SGP,PC,RAR,GDD,EMGDD,TrplShockGDD,TrplGDD,SLA,FCO2,Diluted):
######################## 数据初始化 ########################
    a11= []
    TempGDD = 0.0
    AWLVGSeq = []
    ABIOMASSSeq = []
    ABIOMASS1 = 0.0 # 总生物量
    ATOPWTSeq = []
    AWLVG = 0.1# 绿叶重
    WSTSeq = []
    WST = 0.2# 茎鞘重
    W = 0
    AWSP = 0.01
    AROOTWTSeq = []
    AROOTWT = 0.001
    WSPSeq = []  # 穗重
    WSP =0.01  # 穗重
    LAI = 0.01  # 叶面积指数
    ATOPWT = 0.01  # 地上部
    YIELDSeq = []  # 籽粒产量
    YIELD = 0.0
    LowTempSum = 0.0 #低温温度积累
    FT = 1.0 #温度对结实率的影响
    m_outputSWDF2 = 1#水分亏缺因子
    m_outputSWDF1 = 1#水分亏缺因子
    m_outputSWDF1Seq = []
    m_outputFN = 1 #氮亏缺因子
    m_outputSWDF2Seq = []
    WLVGpi = 0.0
    WLVG = 0.0
    dWLVG = 0.0
####################籽粒数与粒重#######################
    dGCTrans= 0.0  #转移的贮存光合产物
    WSTMIN = 0.0 # 穗分化结束时茎秆干物质重
    Flag3 = False # 穗分化是否结束标志位
    dGrainNum = 0.0 #稻粒数
    GRAINWT = 0.0 #  籽粒重kg / ha
    GRAINWTSeq = []
    GRAINWTi = 0.0 #籽粒前一天重量
    dGGRAINWT = 0.0
    PGRAINWTDEM = 0.0 # 每日籽粒潜在增长量kg / ha
    PerGrainW = 0.0 # 单籽粒重mg / 粒
    m_inputGNWT = 0.0 #籽粒重
    PerGrainInit = 3.5 # 灌浆初始期单籽粒重mg / 粒
    Flag4 = False #是否到达灌浆初始期
    grainFillRate = 0.0 # 单籽粒潜在灌浆速率  g/粒
    dGrainNumSeq = [] #籽粒数
################### 数据初始化 ########################
    WGUSS3 = [0.277778, 0.444444, 0.277778]  # 3点法权重
    DIS5 = [0.04691, 0.230753, 0.5, 0.769147, 0.95309]  # 5点法
    WGUSS5 = [0.118464, 0.239314, 0.284444, 0.239314, 0.118464]  # 5点法权重
    counter1 = 1
    counter2 = 1
    counter3 = 1
    counter4 = 1
    counter5 = 1
################茎蘖动态初始化##########################
    PLANTS = (1000 * 1000 * ABIOMASS) / (10000 * TGW)  # 基本苗     万株/ha   0.94-出苗率？
    DTillerNum = 0.0  # 理想条件下的群体茎蘖数（万/ha）
    dTNUMTILLER = 0.0 #当日茎蘖总数
    TNUMTILLERi = 0.0 #前一日总分蘖数 万/ha
    TILLPOPMAX = 900  #万/ha
    LNE = 0.0  # 有效分蘖可靠叶龄
    TILLPOPE = 0.0 #有效分蘖临界期的分蘖数
    Flag1 = False #叶龄是否达到有效分蘖临界期
    TrillerJNum = 0.0 # 拔节时的茎蘖数   万/ha
    Flag2 = False  # 叶龄是否达到拔节叶龄
    dPTNUMTILLER = 0.0 #拔节后每日无效分蘖
    dTNUMTILLERSeq = []  # 茎蘖总数
    dLN = 0.0
    dLNSeq = [] #叶龄
    LAISeq = [] #叶面积指数
    LAI1 = 0.0 #移栽期初始化
################水模块##########################
    m_inputDH = 5 #田埂高度5cm
    m_FloodWH = 0.0 #当日水深
    m_FloodWHSeq = []
    Albedo = 0.23 #裸土反射率
    m_Runoff = 0.0 #径流，单位：mm
    flux = [0,0,0,0,0,0,0,0,0,0] #每层向下水通量
    flow = [0,0,0,0,0,0,0,0,0,0] #层间重新分配水通量
    m_ESp =0.0 #潜在土壤蒸发
    m_ESa =0.0 #实际土壤蒸发

################氮素模块##########################
    SoilTemprature = 0.0
    SoilTempratureSeq = []
    FldUrea = 0
    FldNO3 = 0
    FldNO3Seq= []
    FldNH4 = 0
    FldNH4Seq= []
    FldNH4Seq = []
    UreaHydrolysisState = 0.0 #尿素水解计数器
    dProf = [1,0,0,0,0,0,0,0,0,0]#加入各层土壤肥料比例
    TotN = [0,0,0,0,0,0,0,0,0,0]
    CNR = [0,0,0,0,0,0,0,0,0,0]
    CNRF =[0,0,0,0,0,0,0,0,0,0]
    ANHUMIN = 0.0 #实际腐殖质矿速率  kg N/ha
    RNAC = 0.0 #每层生物固氮量
    NNOM = 0.0
    REQN = 0.0
    NH4ToNO3 = 0.0 #铵态氮转换硝态氮 kg/ha
    NO3ToNH4 = 0.0 #反硝化
    m_NH3loss = 0.0
    tempdNH42 = 0.0
    AllNH3loss = 0.0
    Fld_dUreaout = 0.0
    LimitN = 0.0
    PNDEMRT = 0.0

    TPNDEMSeq = []
    TPNDEM = 0.0
    totANupTop = 0.0 #地上部氮积累量
    totANupTopSeq = []
    NCTop = 0.0 #地上部实际含氮率
    NCTopSeq = []
    totANupRT = 0.0 #地下部氮积累量
    PNDEMTOP = 0.0 #地上部潜在需氮量F
    PNDEMTOPSeq = []
    PNDEMLV = 0.0 #叶片潜在需氮量
    PNDEMGN = 0.0 #籽粒潜在需氮量
    PNDEMST = 0.0 #茎鞘潜在需氮量
    ANupLV = 0.0 # 叶氮积累量
    ANupST = 0.0 # 茎鞘氮积累量
    ANupGN = 0.0 #籽粒氮积累
    ANupSO = 0.0 #穗氮积累量
    dTotNuptake = 0.0
    swSeq = []
    dANUPNO3Seq = []
    dANUPNO3 = [0,0,0,0,0,0,0,0,0,0]


    dTotNuptakeSeq = []
    RootFacNupSeq = []
    dRootPNH4upSeq= []
    dRootPNH4up= [0,0,0,0,0,0,0,0,0,0]
    dRootPNO3upSeq= []
    dRootPNO3up = [0,0,0,0,0,0,0,0,0,0]
    RootFacNup = 0.0
    PNDEMRTSeq= []
    NCSTC = 0.0 #茎秆最大氮浓度
    RGPNFILL = 0.0 #单籽粒潜在累积速率    CERES 中 温度的函数  ug/粒
    MaxGrainNC = min(2.18, PC/5.95 * 100 * 1.2) #水稻籽粒含氮上下限
    MinGrainNC = max(0.85, PC/5.95 * 100 * 0.6)



    nuf = 0.0 #植株N需供比
    nufSeq = []
    FNH4Seq = []
    FNH4 =  [0,0,0,0,0,0,0,0,0,0]
    m_outputFNSeq = []
    totRootPNupSeq = []
    totRootPNup = 0.0
    WFactRootNup = 0.0
    WFactRootNupSeq = []
    dRTDEP = 0.0
    dRTDEPSeq = []
    dRLVSeq = []
    dGRTSeq = []
    dGRT = 0.0
    dTotRLVSeq = []
    dTotRLV = 0.0
    UreaSeq = []
    RLDFSeq = []

    RLNEW = 0.0
    RLNEWSeq = []
    FldUreaSeq= []
    ANupLVSeq = []
    dNH4Seq = []
    counter6 = 1
    tempdANUPNO3 = 0.0
    tempdANUPNH4 = 0.0
    a123 = 0
    FOMSeq = []
    m_KHFTSeq = []
    m_KHFT = 0.0
    accumSoilT = (0.6 * Tmax[0] + 0.4 * Tmin[0]) * 5
    dNH4 = NH4.copy()
    dNo3 = No3.copy()
    sw = sw0.copy()
#################################################################################################################
    # num = len(DL)
    for l in range (0,10):
        FOM[l] = FOM[l] + m_dStubble * WR[l] / WSUM + m_dStraw * WS[l]
        FON[l] = FON[l] + m_dStubble * WR[l] / WSUM * 0.4 / 50 + m_dStraw * WS[l] * 0.4 / 58
        FOMpool[l][0] = FOM[l] * 0.2
        FOMpool[l][1] = FOM[l] * 0.7
        FOMpool[l][2] = FOM[l] * 0.1
        HUM[l] = m_inputOM[l] * 1000 / (dBD[l] * Layer[l] *0.1)
        NHUM[l] = m_inputOM[l] * 0.58 / 16 * 1000 / (dBD[l] * Layer[l] *0.1)
    RLDF = []  # 土壤每层相对根长密度因子
    for l in range(0, 10):
        RLDF.append(0.0)
    # 查找PDT中最接近58的值的索引（成熟天数）
    # 处理某些品种PDT可能不包含58的情况
    if 58 in PDT:
        position = PDT.index(58)
    else:
        # 找到最接近58的值的索引
        position = min(range(len(PDT)), key=lambda i: abs(PDT[i] - 58) if PDT[i] <= 58 else float('inf'))
        # 如果PDT所有值都大于58，使用第一个索引
        if position == 0 and PDT[0] > 58:
            position = len(PDT) - 1  # 使用最后一个索引

    for i in range(0,position):
        if GDD[i] < EMGDD:
            ###################################################### RiceWBalanceModel ######################################################
            ################### RiceWBalanceModel数据初始化 ########################
            m_Pinf = 0.0  # 灌溉+降雨，单位：mm
            IrriAmount = 0.0  # 每日灌溉量
            m_Ta = 0.0  # 作物根吸水
            dTotRLV = 0.0  # 每天根长数据
            SWcr = []
            for l in range(0, 10):
                SWcr.append(0.0)
            WDurDays = []
            for l in range(0, 10):
                WDurDays.append(0)
            M_DSWDF = []  # 每层土壤水分影响因子M_DSWDF
            for l in range(0, 10):
                M_DSWDF.append(1.0)
            dRupWF = []  # 对根吸水影响因子
            for l in range(0, 10):
                dRupWF.append(0.0)
            dSWF = []
            for l in range(0, 10):
                dSWF.append(1.0)
            dRWU = []  # 作物根吸水
            for l in range(0, 10):
                dRWU.append(0.0)
            ################### 每天根长数据dTotRLV----RiceWBalanceModel----P198 ###################
            for l in range(0, 10):
                dTotRLV = dTotRLV + dRLV[l]
            if dTotRLV <= 0:
                dTotRLV = 100000.0
            ################### 降雨的截留----RiceWBalanceModel----P207 ###################
            if Precip[i] > 0:
                Intcep = (1 - math.exp(-0.65 * LAI)) * 0.2 * ATOPWT / 10000  # 作物截留降雨量
                Precip[i] = Precip[i] - min(Precip[i], Intcep)
                m_Pinf = m_Pinf + Precip[i]
            if (m_FloodWH + m_Pinf / 10) < m_inputDH:
                IrriAmount = (m_inputDH - m_FloodWH - m_Pinf / 10) * 10
                m_FloodWH = m_inputDH
                m_Pinf = m_FloodWH * 10
            else:
                m_FloodWH = m_FloodWH + m_Pinf / 10
                m_Pinf = m_FloodWH * 10 + m_Pinf
                IrriAmount = 0
            ###################################### 作物蒸腾土壤蒸散----RiceWBalanceModel----P273 ######################################
            if m_FloodWH <= 0:
                Albedo = 0.23
            if PDT[i] > 16.2:  # 拨节后
                Albedo = 0.23 + math.pow(LAI, 2) / 160
            elif PDT[i] < 16.2:
                Albedo = 0.23 - (0.23 - Albedo) * math.exp(-0.75 * LAI)
            ######### 参考作物潜在蒸散m_ETpRe ###################
            m_ETpRe = Kt[i] * Q[i] / 1000000 * (0.00488 - 0.00437 * Albedo) * (dTmean[i] + 29)
            ################### 作物潜在蒸散m_ETp ###################
            m_ETp = 0.0
            if LAI <= 1.5:
                m_ETp = m_ETpRe
            elif 1.5 < LAI < 5:
                m_ETp = ((1.66 - 1) * LAI + (5 - 1.5 * 1.66)) * m_ETpRe / 3.5
            else:
                m_ETp = 1.66 * m_ETpRe
            ################### 潜在土壤蒸散m_ESp  &&   潜在作物蒸腾m_Tp ###################
            if m_FloodWH <= 0:
                if LAI < 1.0:
                    m_ESp = m_ETp * math.exp(1 - 0.43 * LAI)
                else:
                    m_ESp = m_ETp * math.exp(-0.65 * LAI)

                if sw[0] > dul[0]:
                    m_ESa = m_ESp
                elif sw[0] < ll[0] / 3:
                    m_ESa = 0.0
                else:
                    m_ESa = m_ESp * (sw[0] - ll[0] / 3) / (dul[0] - ll[0] / 3)
            else:
                if LAI < 0.85:
                    m_ESp = m_ETp * (1 - 0.45 * LAI)
                else:
                    m_ESp = m_ETp * math.exp(-0.65 * LAI)
                m_ESa = m_ESp
            m_Tp = m_ETp - m_ESp  # 潜在作物蒸腾=作物潜在蒸散-土壤蒸发
            ###################################### 灌溉入渗----RiceWBalanceModel----P370 ######################################
            Pinf = m_Pinf / 10.0  # mm->cm
            m_FSSW = 0  # 积水深度
            p_Pinf = Pinf
            for l in range(0, 10):
                flux[l] = 0
                flow[l] = 0
            HoldW = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            for l in range(0, 10):
                HoldW[l] = (sat[l] - sw[l]) * Layer[l]
                if p_Pinf == 0:
                    break
                if p_Pinf <= HoldW[l]:
                    sw[l] = sw[l] + p_Pinf / Layer[l]  # 田间实际含水量变化
                    if sw[l] < (dul[l] + 0.003):
                        p_Pinf = 0.0
                    else:
                        p_Pinf = min((sw[l] - dul[l]) * Layer[l], 0.5)
                        flux[l] = p_Pinf  # 每层水通量
                        sw[l] = sw[l] - p_Pinf / Layer[l]
                else:
                    tempPinf = p_Pinf
                    if sw[l] < dul[l]:
                        p_Pinf = min(p_Pinf - (dul[l] - sw[l]) * Layer[l], 0.5)
                        # p_Pinf = min(p_Pinf - ( sw[l]) * Layer[l], 0.5)
                        flux[l] = p_Pinf
                    else:
                        p_Pinf = min(p_Pinf + (sw[l] - dul[l]) * Layer[l], 0.5)
                        flux[l] = p_Pinf
                    sw[l] = sw[l] + (tempPinf - p_Pinf) / Layer[l]
                    if sw[l] > sat[l]:
                        if l == 0:
                            m_FSSW = m_FSSW + (sw[l] - sat[l]) * Layer[l]
                            sw[l] = sat[l]
                        for ii in range(l - 1, -1, -1):
                            delta = (sw[ii + 1] - sat[ii + 1]) * Layer[ii + 1] / Layer[ii]
                            sw[ii] += delta
                            flux_delta = (sw[ii + 1] - sat[ii + 1]) * Layer[ii + 1]
                            flux[ii] -= flux_delta
                            sw[ii + 1] = sat[ii + 1]
                            if sw[ii] < sat[ii]:
                                break
                            if ii == 0 and sw[ii] > sat[ii]:
                                m_FSSW += (sw[ii] - sat[ii]) * Layer[ii]
                                sw[0] = sat[0]
            m_FloodWH = m_FSSW
            ###################################### 作物根吸水m_Ta----RiceWBalanceModel----P305 ######################################
            for l in range(0, 10):
                if sw[l] < ll[l]:
                    dRupWF[l] = 0.0
                elif sw[l] < dul[l]:
                    dRupWF[l] = math.pow((sw[l] - ll[l]) / (dul[l] - ll[l]), 0.7)
                else:
                    dRupWF[l] = 1.0
                dRWU[l] = m_Tp * dRupWF[l] * dRLV[l] / dTotRLV
                m_Ta = m_Ta + dRWU[l]
            m_ETa = m_ESa + m_Ta
            ###################################### 径流----RiceWBalanceModel----P329 ######################################
            if m_FloodWH > 5:
                m_Runoff = m_Runoff + (10 * m_FloodWH) - 5 * 10
                m_FloodWH = 5
                m_Pinf = m_FloodWH * 10
            else:
                m_Runoff = m_Runoff + 0
                m_Pinf = m_Pinf + m_FloodWH * 10

            if m_FloodWH < m_inputDH:
                IrriAmount = (m_inputDH - m_FloodWH) * 10
                m_FloodWH = m_inputDH
                m_Pinf = m_FloodWH * 10
            else:
                m_FloodWH = m_FloodWH
                m_Pinf = m_FloodWH * 10
                IrriAmount = 0
            ###################################### 确定地下水位位置----RiceWBalanceModel----P464 ######################################
            if m_FloodWH > 0:
                Pinf = m_FloodWH
                if Pinf >= (m_ESa + m_Ta) / 10:
                    Pinf = Pinf - (m_ESa + m_Ta) / 10
                    m_FloodWH = Pinf
                else:
                    tempDemand = (m_ESa + m_Ta) / 10 - Pinf
                    for l in range(0, 10):
                        dMaxSupportW = (sat[l] - dul[l]) * Layer[l]
                        tempDemand = tempDemand - dMaxSupportW
                        if tempDemand < 0:
                            sw[l] = dul[l] - tempDemand / Layer[l]
                            break
                        sw[l] = dul[l]
                    Pinf = 0
                    m_FloodWH = Pinf
            ###################################### 计算水分影响因子----RiceWBalanceModel----P661 ######################################
            SWF = 1
            m_outputSWDF1 = 1.0  # 光合
            m_outputSWDF2 = 1.0  # 分配
            m_outputSWDF3 = 1.0  # 叶面积扩展
            if PDT[i] <= 0:
                m_outputSWDF1 = 1.0
                m_outputSWDF2 = 1.0
                m_outputSWDF3 = 1.0
            else:
                if m_Ta > 0 and m_Tp > 0:
                    SWF = m_Ta / m_Tp
                if SWF > 1:
                    SWF = 1
                m_outputSWDF1 = SWF
                m_outputSWDF2 = 0.5 + SWF / 2
                m_outputSWDF3 = SWF
            ###################################### 每层土壤水分影响因子----RiceWBalanceModel----P745 ######################################
            for l in range(0, 10):
                M_DSWDF[l] = 1.0
            ######################### 土壤温度计算ComputeSoilTemprature ########################-------------------------有问题
            # for l in range(0,4):
            #     FiveDayAveST[l] = 0.6 * Tmax[i] + 0.4 * Tmin[i]

            pesw = 0.0
            m_inputMaxDepth = 0.0
            f = AvedBD / (AvedBD + 686 * math.exp(-5.63 * AvedBD))  ####
            dp = 1000 + 2500 * f  ####
            p = 0.356 - 0.144 * AvedBD  ####
            b = math.log10(500 / dp)  ####
            SolRad = Q[i] / 25000000
            # print sw
            for l in range(0, 10):
                pesw = pesw + (sw[l] - ll[l]) * Layer[l]
                m_inputMaxDepth = m_inputMaxDepth + Layer[l]
            if pesw < 0:
                pesw = 0.01
            alx = 2 * math.pi * (DOY[i] - 200) / 365  ###
            accumSoilT = accumSoilT - FiveDayAveST[4]
            for t in [4, 3, 2, 1]:
                FiveDayAveST[t] = FiveDayAveST[t - 1]
            FiveDayAveST[0] = (1 - 0.23) * (dTmean[i] + (Tmax[i] - dTmean[i]) * math.sqrt(SolRad / 800)) + 0.23 * FiveDayAveST[0]  ####
            accumSoilT = accumSoilT + FiveDayAveST[0]
            wc = pesw / (p * m_inputMaxDepth)  # ----------------------
            ff = math.exp(b * math.pow((1 - wc) / (1 + wc), 2))
            dampingDepth = ff * dp  # 当天土壤的湿润深度
            TA_1 = MeanYearTemp + (MaxMonthTemp - MinMonthTemp) * math.cos(alx) * 0.5  ####
            DT = accumSoilT / 5 - TA_1  # 地表温度五日滑动平均与当日长期平均气温的差值
            zd = -15 / dampingDepth
            SoilTemprature = MeanYearTemp + ((MaxMonthTemp - MinMonthTemp) * math.cos(alx + zd) * 0.5 + DT) * math.exp(zd)
            ###########################################氮素模块###################################################
            ######################## 尿素水解 ########################

            FT = math.pow(1.96, (SoilTemprature - 25) / 10)
            UreaToNH4 = 0.0
            if UREA[i] > 0:
                UreaHydrolysisState = 21
                if m_FloodWH > 0:  # 总施肥量
                    FldUrea = FldUrea + UREA[i]
            if UreaHydrolysisState == 0:
                for l in range(0, 10):
                    # dNH4[l] = dNH4[l] + Urea[l]
                    Urea[l] = 0.0
                if m_FloodWH > 0:
                    # FldNH4 = FldNH4 + FldUrea
                    FldUrea = 0
                UreaHydrolysisState = -1  # 计数器
            elif UreaHydrolysisState > 0:
                # if  m_FloodWH > 0:
                #     FldT = 0.6 * Tmax[i] + Tmin[i] * 0.4
                #     FT1 = math.pow(1.96, (FldT - 25) / 10)
                #     TempUrea = FldUrea
                #     FldUrea = FldUrea * math.exp(-0.744 * FT1)
                #     FldNH4 = FldNH4 + (TempUrea - FldUrea)

                for l in range(0, 10):
                    mf = 0.0
                    if sw[l] < dul[l]:
                        mf = (sw[l] - ll[l]) / (dul[l] - ll[l])
                    else:
                        mf = 1.0 - 0.5 * (sw[l] - dul[l]) / (sat[l] - dul[l])
                    FW = mf + 0.2
                    if FW > 1.0:
                        FW = 1.0
                    elif FW < 0:
                        FW = 0.0
                    if m_FloodWH > 0:
                        FW = 1.0
                    TempUrea = Urea[l]
                    Urea[l] = Urea[l] * math.exp(-0.744 * min(FW, FT))
                    UreaToNH4 = UreaToNH4 + (TempUrea - Urea[l]) * (dBD[l] * Layer[l] * 0.1)
                    dNH4[l] = dNH4[l] + (TempUrea - Urea[l]) / (dBD[l] * Layer[l] * 0.1)
                    if Urea[l] < 0.0001:
                        dNH4[l] = dNH4[l] + Urea[l]
                        Urea[l] = 0
                UreaHydrolysisState = UreaHydrolysisState - 1
            # ############# 计算硝态氮的淋失 ########################
            Fld_dNO3out = 0
            Fld_dNH4out = 0
            Fld_dUreaout = 0
            Runoff_N = 0
            if m_FloodWH > 0:
                Fld_dNO3out = FldNO3 * 0.3
                Fld_dNH4out = FldNH4 * 0.3
                Fld_dUreaout = FldUrea * 0.3
                FldNO3 = FldNO3 - Fld_dNO3out
                FldNH4 = FldNH4 - Fld_dNH4out
                FldUrea = FldUrea - Fld_dUreaout
            for l in range(0, 10):
                if dNo3[l] > 6:
                    dNO3out[l] = 0.9 * (dNo3[l] - 6) * flux[l] / (sw[l] * Layer[l] + flux[l])
                    dNO3up[l] = 0.9 * (dNo3[l] - 6) * flow[l] / (sw[l] * Layer[l] + flow[l])
                else:
                    dNO3out[l] = 0.0
                    dNO3up[l] = 0.0
                if Urea[l] > 5:
                    dUreaOut[l] = 0.8 * (Urea[l] - 5) * flux[l] / (sw[l] * Layer[l] + flux[l])
                    dUreaUp[l] = 0.8 * (Urea[l] - 5) * flow[l] / (sw[l] * Layer[l] + flow[l])
                else:
                    dUreaOut[l] = 0.0
                    dUreaUp[l] = 0.0
                if dNH4[l] > 3:
                    dNH4out[l] = 0.2 * (dNH4[l] - 3) * flux[l] / (sw[l] * Layer[l] + flux[l])
                    dNH4up[l] = 0.2 * (dNH4[l] - 3) * flow[l] / (sw[l] * Layer[l] + flow[l])
                else:
                    dNH4out[l] = 0.0
                    dNH4up[l] = 0.0
                if l == 0:
                    dNO3up[l] = 0.0
                    dNH4up[l] = 0.0
                    dUreaUp[l] = 0.0
                    dNo3[l] = dNo3[l] + Fld_dNO3out + dNO3up[1] - dNO3up[l] - dNO3out[l]
                    dNH4[l] = dNH4[l] + Fld_dNH4out + dNH4up[1] - dNH4up[l] - dNH4out[l]
                    Urea[l] = Urea[l] + Fld_dUreaout + dUreaUp[1] - dUreaUp[l] - dUreaOut[l]
                else:
                    if l < 9:
                        dNo3[l] = dNo3[l] + dNO3out[l - 1] + dNO3up[l + 1] - dNO3up[l] - dNO3out[l]
                        dNH4[l] = dNH4[l] + dNH4out[l - 1] + dNH4up[l + 1] - dNH4up[l] - dNH4out[l]
                        Urea[l] = Urea[l] + dUreaOut[l - 1] + dUreaUp[l + 1] - dUreaUp[l] - dUreaOut[l]
                    else:
                        dNo3[l] = dNo3[l] + dNO3out[l - 1] - dNO3up[l] - dNO3out[l]
                        dNH4[l] = dNH4[l] + dNH4out[l - 1] - dNH4up[l] - dNH4out[l]
                        Urea[l] = Urea[l] + dUreaOut[l - 1] - dUreaUp[l] - dUreaOut[l]
            ######################## 计算土壤有机质矿化 ########################
            m_KHFW = []
            for l in range(0, 10):
                m_KHFW.append(0.0)
            # ######################## 累积新鲜有机质与新鲜有机质氮含量及腐殖质和腐殖质氮量########################
            ######################## 总新鲜有机质释放N ########################
            DecoR = [0.8, 0.05, 0.0095]  # 三种组分的分解速率
            dKH = []  # 每天矿化量
            Tgrncom = 0.0
            MinerN = 0.0
            m_KHFT = 0.9 * SoilTemprature / (math.exp(9.93 - 0.35 * SoilTemprature) + SoilTemprature) + 0.1
            if SoilTemprature < 5.0:
                m_KHFT = 0.0
            for l in range(0, 10):
                TotN[l] = (dNH4[l] + dNo3[l]) * (dBD[l] * Layer[l] * 0.1)
                CNR[l] = (0.4 * FOM[l]) / (FON[l] + TotN[l])
                CNRF[l] = math.exp(-0.693 * (CNR[l] - 25.0) / 25.0)  # C/N对矿化的影响
                if CNRF[l] > 1:
                    CNRF[l] = 1
                if CNRF[l] <= 0:
                    CNRF[l] = 0.00001
                grcom = 0.0
                grncom = 0.0
                if sw[l] < dul[l]:
                    m_KHFW[l] = (sw[l] - ll[l]) / (dul[l] - ll[l])
                else:
                    m_KHFW[l] = 1.0 - 0.5 * (sw[l] - dul[l]) / (sat[l] - dul[l])
                REQN = 0.02
                if m_FloodWH > 0:
                    m_KHFW[l] = 0.75
                    REQN = 0.01
                for j in range(0, 3):
                    if FOMpool[l][j] < 5:
                        g = 0.0
                    else:
                        g = m_KHFT * m_KHFW[l] * CNRF[l] * DecoR[j]
                    FOMpool[l][j] = FOMpool[l][j] - FOMpool[l][j] * g
                    grcom = grcom + FOMpool[l][j] * g
                    grncom = grncom + FON[l] * FOMpool[l][j] * g / FOM[l]
                    Tgrncom = Tgrncom + grncom  # 总新鲜有机质释放N
                ######################## 总腐殖质释放N ########################
                ANHUMIN = NHUM[l] * 0.000215 * m_KHFT * m_KHFW[l] * 1.0  # 0.000215土壤矿化率 * 0.0001
                HUM[l] = HUM[l] - ANHUMIN * 16.0 / 0.58 + 0.2 * grncom * 16 / 0.4
                NHUM[l] = NHUM[l] - ANHUMIN + 0.2 * grncom
                RNAC = min(TotN[l], grcom * (REQN - FON[l] / FOM[l]))
                if RNAC < 0:
                    RNAC = 0.0
                NNOM = 0.8 * grncom + ANHUMIN - RNAC
                if NNOM < 0:
                    NNOM = 0.0
                MinerN = MinerN + NNOM
                if NNOM > 0:
                    dNH4[l] = dNH4[l] + NNOM / (dBD[l] * Layer[l] * 0.1)
                else:
                    if math.fabs(NNOM) > (dNH4[l] - 0.5) * (dBD[l] * Layer[l] * 0.1):
                        NNOM = NNOM + (dNH4[l] - 0.5) * (dBD[l] * Layer[l] * 0.1)
                        dNH4[l] = 0.5
                    else:
                        dNH4[l] = dNH4[l] + NNOM / (dBD[l] * Layer[l] * 0.1)
                        NNOM = 0.0
                    dNo3[l] = dNo3[l] + NNOM / (dBD[l] * Layer[l] * 0.1)
            m_TotalKHN = MinerN  # 硝态氮反硝化铵态氮//kg/ha
            ######################## 计算硝化作用 ########################
            NH4ToNO3_1 = 0.0  # 硝化作用
            m_minNO3 = 0.25  # 土壤中硝态氮最低氮浓度
            m_minNH4 = 0.5  # 土壤中铵态氮最低氮浓度
            m_dNitrif = [0.0] * 10
            FldNtfrate = 0
            if m_FloodWH > 0:
                FLdTemperature = 0.6 * Tmax[i] + 0.4 * Tmin[i]
                if FLdTemperature < 5:
                    FTn = 0
                else:
                    FTn = (FLdTemperature - 5) / 30
                Knitr = 0.08
                tempFldNH4 = FldNH4 * math.exp(-Knitr * FTn)
                FldNtfrate = FldNH4 - tempFldNH4
                FldNH4 = FldNH4 - FldNtfrate
                FldNO3 = FldNO3 + FldNtfrate
            m_ntFT = [0.0] * 10  # 温度对硝化作用的影响
            m_ntFW = [0.0] * 10  # 水分对硝化作用的影响
            for l in range(0, 10):
                if SoilTemprature < 5:
                    m_ntFT[l] = 0
                else:
                    m_ntFT[l] = (SoilTemprature - 5) / 30
                if sw[l] < dul[l] * 0.6:
                    m_ntFW[l] = (sw[l] - ll[l]) / (dul[l] * 0.6 - ll[l])
                elif sw[l] < dul[l]:
                    m_ntFW[l] = 1
                else:
                    m_ntFW[l] = 1 - (sw[l] - dul[l]) / (sat[l] - dul[l])
                if m_ntFW[l] < 0:
                    m_ntFW[l] = 0
                aa = dNH4[l] - m_minNH4
                tempdNH4 = dNH4[l] * math.exp(-0.2 * min(m_ntFT[l], m_ntFW[l], m_ntFPH[l]))
                m_dNitrif[l] = dNH4[l] - tempdNH4
                if aa <= 0:
                    m_dNitrif[l] = 0
                NH4ToNO3_1 = NH4ToNO3_1 + m_dNitrif[l] * (dBD[l] * Layer[l] * 0.1)
                dNo3[l] = dNo3[l] + m_dNitrif[l]
                dNH4[l] = dNH4[l] - m_dNitrif[l]
            NH4ToNO3 = NH4ToNO3 + NH4ToNO3_1
            ######################## 计算反硝化作用 ########################
            m_dDNitrif = [0.0] * 10
            NO3ToNH4_1 = 0.0
            # m_dntFW = 0.0 #反硝化作用的水分影响因子
            # m_dntFT = 0.0#反硝化作用的温度影响因子
            Kdn = 0.1
            for l in range(0, 10):
                # if m_FloodWH > 0:
                #     m_dDNitrif[l] = max((dNo3[l] - m_minNO3), 0)
                #     dNo3[l] = m_minNO3
                #     dNH4[l] = dNH4[l] + m_dDNitrif[l]
                if SoilTemprature > 5 and dNo3[l] > 1 and sw[l] > dul[l]:
                    m_dntFW = 1 - (sat[l] - sw[l]) / (sat[l] - dul[l])
                    m_dntFT = 0.1 * math.exp(0.046 * SoilTemprature)
                    dd = dNo3[l] - m_minNO3
                    tempdNO3 = dNo3[l] * math.exp(-Kdn * min(m_dntFW, m_dntFT))
                    TempDN = dNo3[l] - tempdNO3
                    m_dDNitrif[l] = min(TempDN, dd)
                    if m_dDNitrif[l] < 0:
                        m_dDNitrif[l] = 0
                        dNo3[l] = m_minNO3
                    dNo3[l] = dNo3[l] - m_dDNitrif[l]
                    # dNH4[l] = dNH4[l] + m_dDNitrif[l]
                    NO3ToNH4_1 = NO3ToNH4_1 + m_dDNitrif[l] * (dBD[l] * Layer[l] * 0.1)
            NO3ToNH4 = NO3ToNH4 + NO3ToNH4_1
            ####################### 计算氨挥发损失 ########################
            FldNH3Vloss = 0
            Kv = 0.05
            m_volatFT = 0.4 * (25.41 - 10) / 10
            m_voltFH = math.pow(10, (dPH[0] - 7.5))
            if m_FloodWH > 0:
                FLdT = 0.6 * Tmax[i] + Tmin[i] * 0.4
                FldFT = 0.41 * (FLdT - 10.0) / 10
                if FldFT > 1:
                    FLdT = 1
                if FldFT < 0:
                    FLdT = 0
                tempFldnh4 = FldNH4 * math.exp(-Kv * FldFT)
                FldNH3Vloss = FldNH4 - tempFldnh4
                if FldNH3Vloss < 0:
                    FldNH3Vloss = 0.0
                FldNH4 = tempFldnh4  # 淹水中铵态氮含量
                m_NH3loss = 0
            else:
                if dNH4[0] > 2:
                    tempdNH42 = (dNH4[0] - 0.5) * math.exp(-0.05 * min(m_volatFT, m_voltFH))
                    m_NH3loss = (dNH4[0] - 0.5) - tempdNH42
                    dNH4[0] = dNH4[0] - m_NH3loss

                else:
                    m_NH3loss = 0.0
            AllNH3loss = FldNH3Vloss + m_NH3loss
            ####################### 剖面土壤可供应总氮量 ########################
            TAN = 0.0  # 耕层剖面可供氮量 kg/ha
            if m_FloodWH > 0:
                TAN = TAN + (FldNO3 + FldNH4 + FldUrea) * m_FloodWH * 0.1
            tempD = 0.0
            for l in range(0, 10):
                tempD = tempD + Layer[l]
                if tempD <= 26:
                    dTotAN[l] = dNo3[l] + dNH4[l] + Urea[l]
                    TAN = TAN + dTotAN[l] * (dBD[l] * Layer[l] * 0.1)
                elif (tempD - Layer[l]) <= 26:
                    dTotAN[l] = dNo3[l] + dNH4[l] + Urea[l]
                    TAN = TAN + dTotAN[l] * (dBD[l] * Layer[l] * 0.1) * (26 + Layer[l] - tempD) / Layer[l]

######################## 物质生产及分配 ########################
        if GDD[i] >= EMGDD:
            if GDD[i] > TrplGDD and counter2 == 1:

                dNH4 = NH4.copy()
                dNo3 = No3.copy()
                sw = sw0.copy()  # 土层实际含水量
                FOM = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # 新鲜有机质
                FON = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # 新鲜有机质氮含量
                for l in range(0, 10):
                    FOM[l] = FOM[l] + m_dStubble * WR[l] / WSUM + m_dStraw * WS[l]
                    FON[l] = FON[l] + m_dStubble * WR[l] / WSUM * 0.4 / 50 + m_dStraw * WS[l] * 0.4 / 58
                    FOMpool[l][0] = FOM[l] * 0.2
                    FOMpool[l][1] = FOM[l] * 0.7
                    FOMpool[l][2] = FOM[l] * 0.1
                    HUM[l] = m_inputOM[l] * 1000 / (dBD[l] * Layer[l] * 0.1)
                    NHUM[l] = m_inputOM[l] * 0.58 / 16 * 1000 / (dBD[l] * Layer[l] * 0.1)
                counter2 = -1
###################################################### RiceWBalanceModel ######################################################
################### RiceWBalanceModel数据初始化 ########################
            m_Pinf = 0.0  # 灌溉+降雨，单位：mm
            IrriAmount = 0.0 #每日灌溉量
            m_Ta = 0.0  # 作物根吸水
            dTotRLV = 0.0  # 每天根长数据
            SWcr = []
            for l in range(0, 10):
                SWcr.append(0.0)
            WDurDays = []
            for l in range(0, 10):
                WDurDays.append(0)
            M_DSWDF = []  # 每层土壤水分影响因子M_DSWDF
            for l in range(0, 10):
                M_DSWDF.append(1.0)
            dRupWF = []  # 对根吸水影响因子
            for l in range(0, 10):
                dRupWF.append(0.0)
            dSWF = []
            for l in range(0, 10):
                dSWF.append(1.0)
            dRWU = []  # 作物根吸水
            for l in range(0, 10):
                dRWU.append(0.0)
################### 每天根长数据dTotRLV----RiceWBalanceModel----P198 ###################
            # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
            for l in range(0, 10):
                dTotRLV = dTotRLV + dRLV[l]
            if dTotRLV <= 0:
                dTotRLV = 100000.0
################### 降雨的截留----RiceWBalanceModel----P207 ###################
            if Precip[i] > 0:
                Intcep = (1 - math.exp(-0.65 * LAI)) * 0.2 * ATOPWT / 10000  # 作物截留降雨量
                Precip[i] = Precip[i] - min(Precip[i], Intcep)
                m_Pinf = m_Pinf + Precip[i]
            if (m_FloodWH+m_Pinf/10 ) < m_inputDH:
                IrriAmount = (m_inputDH - m_FloodWH - m_Pinf / 10) * 10
                m_FloodWH = m_inputDH
                m_Pinf = m_FloodWH * 10
            else:
                m_FloodWH = m_FloodWH + m_Pinf/10
                m_Pinf = m_FloodWH*10 + m_Pinf
                IrriAmount = 0
###################################### 作物蒸腾土壤蒸散----RiceWBalanceModel----P273 ######################################
            if m_FloodWH<=0:
                Albedo = 0.23
            if PDT[i] > 16.2:  # 拨节后
                Albedo = 0.23 + math.pow(LAI, 2) / 160
            elif PDT[i] < 16.2:
                Albedo = 0.23 -(0.23 - Albedo)* math.exp(-0.75*LAI)
######### 参考作物潜在蒸散m_ETpRe ###################
            m_ETpRe = Kt[i]* Q[i] / 1000000 * (0.00488 - 0.00437 * Albedo) * (dTmean[i] + 29)
################### 作物潜在蒸散m_ETp ###################
            m_ETp = 0.0
            if LAI <= 1.5:
                m_ETp = m_ETpRe
            elif 1.5 < LAI < 5:
                m_ETp = ((1.66 - 1) * LAI + (5 - 1.5 * 1.66)) * m_ETpRe / 3.5
            else:
                m_ETp = 1.66 * m_ETpRe
################### 潜在土壤蒸散m_ESp  &&   潜在作物蒸腾m_Tp ###################
            if m_FloodWH <= 0:
                if LAI < 1.0:
                    m_ESp = m_ETp * math.exp(1-0.43 * LAI)
                else:
                    m_ESp = m_ETp * math.exp(-0.65 * LAI)

                if sw[0] > dul[0]:
                    m_ESa = m_ESp
                elif sw[0] < ll[0]/3:
                    m_ESa = 0.0
                else:
                    m_ESa = m_ESp * (sw[0] - ll[0]/3) / (dul[0] - ll[0]/3)
            else:
                if LAI < 0.85:
                    m_ESp = m_ETp * (1-0.45 * LAI)
                else:
                    m_ESp = m_ETp * math.exp(-0.65 * LAI)
                m_ESa = m_ESp
            m_Tp = m_ETp - m_ESp #潜在作物蒸腾=作物潜在蒸散-土壤蒸发
            ###################################### 灌溉入渗----RiceWBalanceModel----P370 ######################################
            Pinf = m_Pinf / 10.0  # mm->cm
            m_FSSW = 0  # 积水深度
            p_Pinf = Pinf
            for l in range(0, 10):
                flux[l] = 0
                flow[l] = 0
            HoldW = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            for l in range(0, 10):
                HoldW[l] = (sat[l] - sw[l]) * Layer[l]
                if p_Pinf == 0:
                    break
                if p_Pinf <= HoldW[l]:
                    sw[l] = sw[l] + p_Pinf / Layer[l]  # 田间实际含水量变化
                    if sw[l] < (dul[l] + 0.003):
                        p_Pinf = 0.0
                    else:
                        p_Pinf = min((sw[l] - dul[l]) * Layer[l], 0.5)
                        flux[l] = p_Pinf  # 每层水通量
                        sw[l] = sw[l] - p_Pinf / Layer[l]
                else:
                    tempPinf = p_Pinf
                    if sw[l] < dul[l]:
                        p_Pinf = min(p_Pinf - (dul[l] - sw[l]) * Layer[l], 0.5)
                        # p_Pinf = min(p_Pinf - ( sw[l]) * Layer[l], 0.5)
                        flux[l] = p_Pinf
                    else:
                        p_Pinf = min(p_Pinf + (sw[l] - dul[l]) * Layer[l], 0.5)
                        flux[l] = p_Pinf
                    sw[l] = sw[l] + (tempPinf - p_Pinf) / Layer[l]
                    if sw[l] > sat[l]:
                        if l == 0:
                            m_FSSW = m_FSSW + (sw[l] - sat[l]) * Layer[l]
                            sw[l] = sat[l]
                        for ii in range(l - 1, -1, -1):
                            delta = (sw[ii + 1] - sat[ii + 1]) * Layer[ii + 1] / Layer[ii]
                            sw[ii] += delta
                            flux_delta = (sw[ii + 1] - sat[ii + 1]) * Layer[ii + 1]
                            flux[ii] -= flux_delta
                            sw[ii + 1] = sat[ii + 1]
                            if sw[ii] < sat[ii]:
                                break
                            if ii == 0 and sw[ii] > sat[ii]:
                                m_FSSW += (sw[ii] - sat[ii]) * Layer[ii]
                                sw[0] = sat[0]
            m_FloodWH = m_FSSW
###################################### 作物根吸水m_Ta----RiceWBalanceModel----P305 ######################################
            for l in range(0, 10):
                if sw[l] < ll[l]:
                    dRupWF[l] = 0.0
                elif sw[l] < dul[l]:
                    dRupWF[l] = math.pow((sw[l] - ll[l]) / (dul[l] - ll[l]), 0.7)
                else:
                    dRupWF[l] = 1.0
                # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                dRWU[l] = m_Tp * dRupWF[l] * dRLV[l] / dTotRLV

                m_Ta = m_Ta + dRWU[l]
            m_ETa = m_ESa + m_Ta
###################################### 径流----RiceWBalanceModel----P329 ######################################
            if m_FloodWH > 5:
                m_Runoff = m_Runoff +(10 * m_FloodWH ) - 5 * 10
                m_FloodWH = 5
                m_Pinf = m_FloodWH * 10
            else:
                m_Runoff = m_Runoff + 0
                m_Pinf = m_Pinf + m_FloodWH * 10

            if m_FloodWH  < m_inputDH:
                IrriAmount = (m_inputDH - m_FloodWH ) * 10
                m_FloodWH = m_inputDH
                m_Pinf = m_FloodWH * 10
            else:
                m_FloodWH = m_FloodWH
                m_Pinf = m_FloodWH * 10
                IrriAmount = 0
###################################### 确定地下水位位置----RiceWBalanceModel----P464 ######################################
            if m_FloodWH > 0:
                Pinf = m_FloodWH
                if Pinf >= (m_ESa + m_Ta) / 10:
                    Pinf = Pinf - (m_ESa + m_Ta) / 10
                    m_FloodWH = Pinf
                else:
                    tempDemand = (m_ESa + m_Ta) / 10 - Pinf
                    for l in range(0,10):
                        dMaxSupportW = (sat[l] - dul[l]) * Layer[l]
                        tempDemand = tempDemand - dMaxSupportW
                        if tempDemand < 0:
                            sw[l] = dul[l] - tempDemand / Layer[l]
                            break
                        sw[l] = dul[l]
                    Pinf = 0
                    m_FloodWH = Pinf
###################################### 计算水分影响因子----RiceWBalanceModel----P661 ######################################
            SWF = 1
            m_outputSWDF1 = 1.0  # 光合
            m_outputSWDF2 = 1.0  # 分配
            m_outputSWDF3 = 1.0  # 叶面积扩展
            if PDT[i] <= 0:
                m_outputSWDF1 = 1.0
                m_outputSWDF2 = 1.0
                m_outputSWDF3 = 1.0
            else:
                if m_Ta > 0 and m_Tp>0:
                    SWF = m_Ta / m_Tp
                if SWF > 1:
                    SWF = 1
                m_outputSWDF1 = SWF
                m_outputSWDF2 = 0.5 + SWF / 2
                m_outputSWDF3 = SWF
###################################### 每层土壤水分影响因子----RiceWBalanceModel----P745 ######################################
            for l in range(0, 10):
                M_DSWDF[l] = 1.0
######################### 土壤温度计算ComputeSoilTemprature ########################-------------
            # for l in range(0,4):
            #     FiveDayAveST[l] = 0.6 * Tmax[i] + 0.4 * Tmin[i]

            pesw = 0.0
            m_inputMaxDepth = 0.0
            f = AvedBD / (AvedBD + 686 * math.exp(-5.63 * AvedBD))  ####
            dp = 1000 + 2500 * f  ####
            p = 0.356 - 0.144 * AvedBD  ####
            b = math.log10(500 / dp)  ####
            SolRad = Q[i] / 25000000
            # print sw
            for l in range(0, 10):
                pesw = pesw + (sw[l] - ll[l]) * Layer[l]
                m_inputMaxDepth = m_inputMaxDepth + Layer[l]
            if pesw < 0:
                pesw = 0.01
            alx = 2 * math.pi * (DOY[i] - 200) / 365  ###
            accumSoilT = accumSoilT - FiveDayAveST[4]
            for t in [4, 3, 2, 1]:
                FiveDayAveST[t] = FiveDayAveST[t - 1]
            FiveDayAveST[0] = (1 - 0.23) * (dTmean[i] + (Tmax[i] - dTmean[i]) * math.sqrt(SolRad / 800)) + 0.23 * FiveDayAveST[0]  ####
            accumSoilT = accumSoilT + FiveDayAveST[0]
            wc = pesw / (p * m_inputMaxDepth)  # ----------------------
            ff = math.exp(b * math.pow((1 - wc) / (1 + wc), 2))
            dampingDepth = ff * dp  # 当天土壤的湿润深度
            TA_1 = MeanYearTemp + (MaxMonthTemp - MinMonthTemp) * math.cos(alx) * 0.5  ####
            DT = accumSoilT / 5 - TA_1  # 地表温度五日滑动平均与当日长期平均气温的差值
            zd = -15 / dampingDepth
            SoilTemprature = MeanYearTemp + ((MaxMonthTemp - MinMonthTemp) * math.cos(alx + zd) * 0.5 + DT) * math.exp(zd)
###########################################氮素模块###################################################
######################## 尿素水解 ########################
            a123 =FOMpool[0][0]
            FT = math.pow(1.96, (SoilTemprature - 25) / 10)
            UreaToNH4 = 0.0
            if UREA[i] > 0:
                UreaHydrolysisState = 21
                if m_FloodWH > 0:  # 总施肥量
                    FldUrea = FldUrea + UREA[i]
            if UreaHydrolysisState == 0:
                for l in range(0, 10):
                    # dNH4[l] = dNH4[l] + Urea[l]
                    Urea[l] = 0.0
                if m_FloodWH > 0:
                    # FldNH4 = FldNH4 + FldUrea
                    FldUrea = 0
                UreaHydrolysisState = -1  # 计数器
            elif UreaHydrolysisState > 0:
                # if  m_FloodWH > 0:
                #     FldT = 0.6 * Tmax[i] + Tmin[i] * 0.4
                #     FT1 = math.pow(1.96, (FldT - 25) / 10)
                #     TempUrea = FldUrea
                #     FldUrea = FldUrea * math.exp(-0.744 * FT1)
                #     FldNH4 = FldNH4 + (TempUrea - FldUrea)

                for l in range(0, 10):
                    mf = 0.0
                    if sw[l] < dul[l]:
                        mf = (sw[l] - ll[l]) / (dul[l] - ll[l])
                    else:
                        mf = 1.0 - 0.5 * (sw[l] - dul[l]) / (sat[l] - dul[l])
                    FW = mf + 0.2
                    if FW > 1.0:
                        FW = 1.0
                    elif FW < 0:
                        FW = 0.0
                    if m_FloodWH > 0:
                        FW = 1.0
                    TempUrea = Urea[l]
                    Urea[l] = Urea[l] * math.exp(-0.744 * min(FW, FT))
                    UreaToNH4 = UreaToNH4 + (TempUrea - Urea[l]) * (dBD[l] * Layer[l] * 0.1)
                    dNH4[l] = dNH4[l] + (TempUrea - Urea[l]) / (dBD[l] * Layer[l] * 0.1)
                    if Urea[l] < 0.0001:
                        dNH4[l] = dNH4[l] + Urea[l]
                        Urea[l] = 0
                UreaHydrolysisState = UreaHydrolysisState - 1
# ############# 计算硝态氮的淋失 ########################
            Fld_dNO3out = 0
            Fld_dNH4out = 0
            Fld_dUreaout = 0
            Runoff_N = 0
            if m_FloodWH > 0:
                Fld_dNO3out = FldNO3 * 0.3
                Fld_dNH4out = FldNH4 * 0.3
                Fld_dUreaout = FldUrea * 0.3
                FldNO3 = FldNO3 - Fld_dNO3out
                FldNH4 = FldNH4 - Fld_dNH4out
                FldUrea = FldUrea - Fld_dUreaout
            for l in range(0, 10):
                if dNo3[l] > 6:
                    dNO3out[l] = 0.9 * (dNo3[l] - 6) * flux[l] / (sw[l] * Layer[l] + flux[l])
                    dNO3up[l] = 0.9 * (dNo3[l] - 6) * flow[l] / (sw[l] * Layer[l] + flow[l])
                else:
                    dNO3out[l] = 0.0
                    dNO3up[l] = 0.0
                if Urea[l] > 5:
                    dUreaOut[l] = 0.8 * (Urea[l] - 5) * flux[l] / (sw[l] * Layer[l] + flux[l])
                    dUreaUp[l] = 0.8 * (Urea[l] - 5) * flow[l] / (sw[l] * Layer[l] + flow[l])
                else:
                    dUreaOut[l] = 0.0
                    dUreaUp[l] = 0.0
                if dNH4[l] > 3:
                    dNH4out[l] = 0.2 * (dNH4[l] - 3) * flux[l] / (sw[l] * Layer[l] + flux[l])
                    dNH4up[l] =0.2 * (dNH4[l] - 3) * flow[l] / (sw[l] * Layer[l] + flow[l])
                else:
                    dNH4out[l] = 0.0
                    dNH4up[l] = 0.0
                if l == 0:
                    dNO3up[l] = 0.0
                    dNH4up[l] = 0.0
                    dUreaUp[l] = 0.0
                    dNo3[l] = dNo3[l] + Fld_dNO3out  + dNO3up[1] - dNO3up[l] - dNO3out[l]
                    dNH4[l] = dNH4[l] + Fld_dNH4out   + dNH4up[1] - dNH4up[l] - dNH4out[l]
                    Urea[l] = Urea[l] + Fld_dUreaout  + dUreaUp[1] - dUreaUp[l] - dUreaOut[l]
                else:
                    if l < 9:
                        dNo3[l] =dNo3[l] + dNO3out[l-1] + dNO3up[l+1] - dNO3up[l] - dNO3out[l]
                        dNH4[l] = dNH4[l] +dNH4out[l - 1] + dNH4up[l + 1] - dNH4up[l] - dNH4out[l]
                        Urea[l] = Urea[l] + dUreaOut[l - 1] + dUreaUp[l + 1] - dUreaUp[l] - dUreaOut[l]
                    else:
                        dNo3[l] = dNo3[l] + dNO3out[l - 1]  - dNO3up[l] - dNO3out[l]
                        dNH4[l] = dNH4[l] + dNH4out[l - 1]  - dNH4up[l] - dNH4out[l]
                        Urea[l] = Urea[l] + dUreaOut[l - 1]  - dUreaUp[l] - dUreaOut[l]
######################## 计算土壤有机质矿化 ########################
            m_KHFW = []
            for l in range(0, 10):
                m_KHFW.append(0.0)
# ######################## 累积新鲜有机质与新鲜有机质氮含量及腐殖质和腐殖质氮量########################
######################## 总新鲜有机质释放N ########################
            DecoR = [0.8, 0.05, 0.0095] # 三种组分的分解速率
            dKH = []  # 每天矿化量
            Tgrncom = 0.0
            MinerN = 0.0
            m_KHFT = 0.9 * SoilTemprature / (math.exp(9.93 - 0.35 * SoilTemprature) + SoilTemprature) + 0.1
            if SoilTemprature < 5.0:
                m_KHFT = 0.0
            for l in range(0, 10):
                TotN[l] = (dNH4[l] + dNo3[l]) * (dBD[l] * Layer[l] *0.1)
                CNR[l] = (0.4 * FOM[l]) / (FON[l] + TotN[l])
                CNRF[l] = math.exp(-0.693 * (CNR[l] - 25.0) / 25.0) # C/N对矿化的影响
                if CNRF[l] > 1:
                    CNRF[l] = 1
                if CNRF[l] <= 0:
                    CNRF[l] = 0.00001
                grcom = 0.0
                grncom = 0.0
                if sw[l] < dul[l]:
                    m_KHFW[l] = (sw[l] - ll[l]) / (dul[l] - ll[l])
                else:
                    m_KHFW[l] = 1.0 - 0.5 * (sw[l] - dul[l]) / (sat[l] - dul[l])
                REQN = 0.02
                if m_FloodWH > 0:
                    m_KHFW[l] = 0.75
                    REQN = 0.01
                for j in range(0, 3):
                    if FOMpool[l][j] < 5:
                        g =0.0
                    else:
                        g = m_KHFT * m_KHFW[l] * CNRF[l] *DecoR[j]
                    FOMpool[l][j] = FOMpool[l][j] - FOMpool[l][j] * g
                    grcom = grcom + FOMpool[l][j]* g
                    grncom = grncom + FON[l] * FOMpool[l][j]* g / FOM[l]
                    Tgrncom = Tgrncom + grncom # 总新鲜有机质释放N
        ######################## 总腐殖质释放N ########################
                ANHUMIN = NHUM[l] *   0.000215 * m_KHFT * m_KHFW[l] * 1.0 # 0.000215土壤矿化率 * 0.0001
                HUM[l] = HUM[l] - ANHUMIN * 16.0 / 0.58 + 0.2 * grncom * 16 / 0.4
                NHUM[l] = NHUM[l] - ANHUMIN + 0.2 * grncom
                RNAC = min(TotN[l],grcom * (REQN - FON[l] / FOM[l]))
                if RNAC < 0 :
                    RNAC = 0.0
                NNOM = 0.8 * grncom + ANHUMIN - RNAC
                if NNOM < 0:
                    NNOM = 0.0
                MinerN = MinerN + NNOM
                if NNOM > 0:
                    dNH4[l] = dNH4[l] + NNOM / (dBD[l] * Layer[l] *0.1)
                else:
                    if math.fabs(NNOM) > ((dNH4[l] - 0.5) * (dBD[l] * Layer[l] *0.1)):
                        NNOM = NNOM + (dNH4[l] - 0.5) * (dBD[l] * Layer[l] *0.1)
                        dNH4[l] = 0.5
                    else:
                        dNH4[l] = dNH4[l] + NNOM / (dBD[l] * Layer[l] * 0.1)
                        NNOM = 0.0
                    dNo3[l] =  dNo3[l] + NNOM / (dBD[l] * Layer[l] * 0.1)
            m_TotalKHN = MinerN #硝态氮反硝化铵态氮//kg/ha
######################## 计算硝化作用 ########################
            NH4ToNO3_1 = 0.0 # 硝化作用
            m_minNO3 = 0.25 #土壤中硝态氮最低氮浓度
            m_minNH4 =  0.5 #土壤中铵态氮最低氮浓度
            m_dNitrif = [0.0] * 10
            FldNtfrate = 0
            if m_FloodWH > 0:
                FLdTemperature = 0.6 * Tmax[i] + 0.4 * Tmin[i]
                if FLdTemperature < 5:
                    FTn = 0
                else:
                    FTn = (FLdTemperature - 5) / 30
                Knitr = 0.08
                tempFldNH4 = FldNH4 * math.exp(-Knitr * FTn)
                FldNtfrate = FldNH4 - tempFldNH4
                FldNH4 = FldNH4 - FldNtfrate
                FldNO3 = FldNO3 + FldNtfrate
            m_ntFT = [0.0] * 10 #温度对硝化作用的影响
            m_ntFW = [0.0] * 10 #水分对硝化作用的影响
            for l in range(0,10):
                if SoilTemprature < 5:
                    m_ntFT[l] = 0
                else:
                    m_ntFT[l] = (SoilTemprature - 5) / 30
                if sw[l] < dul[l] * 0.6:
                    m_ntFW[l] = (sw[l] - ll[l]) / (dul[l] * 0.6 - ll[l])
                elif sw[l] < dul[l]:
                    m_ntFW[l] = 1
                else:
                    m_ntFW[l] = 1 - (sw[l] -dul[l] ) / (sat[l] - dul[l])
                if m_ntFW[l] < 0:
                    m_ntFW[l] = 0
                aa = dNH4[l] - m_minNH4
                tempdNH4 = dNH4[l] * math.exp(-0.2 * min(m_ntFT[l], m_ntFW[l], m_ntFPH[l]))
                m_dNitrif[l] = dNH4[l] - tempdNH4
                if aa <= 0:
                    m_dNitrif[l] = 0
                NH4ToNO3_1 = NH4ToNO3_1 + m_dNitrif[l] * (dBD[l] * Layer[l] * 0.1)
                dNo3[l] = dNo3[l] + m_dNitrif[l]
                dNH4[l] =  dNH4[l] - m_dNitrif[l]
            NH4ToNO3 = NH4ToNO3 + NH4ToNO3_1
######################## 计算反硝化作用 ########################
            m_dDNitrif = [0.0] * 10
            NO3ToNH4_1 = 0.0
            # m_dntFW = 0.0 #反硝化作用的水分影响因子
            # m_dntFT = 0.0#反硝化作用的温度影响因子
            Kdn = 0.1
            for l in range(0,10):
                # if m_FloodWH > 0:
                #     m_dDNitrif[l] = max((dNo3[l] - m_minNO3), 0)
                #     dNo3[l] = m_minNO3
                #     dNH4[l] = dNH4[l] + m_dDNitrif[l]
                if SoilTemprature > 5 and dNo3[l] > 1 and sw[l] > dul[l]:
                    m_dntFW = 1 - (sat[l] - sw[l]) / (sat[l] - dul[l])
                    m_dntFT = 0.1 * math.exp(0.046 * SoilTemprature)
                    dd = dNo3[l] - m_minNO3
                    tempdNO3 = dNo3[l] * math.exp(-Kdn * min(m_dntFW, m_dntFT))
                    TempDN = dNo3[l] - tempdNO3
                    m_dDNitrif[l] =min(TempDN, dd)
                    if m_dDNitrif[l] < 0:
                        m_dDNitrif[l] = 0
                        dNo3[l] = m_minNO3
                    dNo3[l] = dNo3[l]-m_dDNitrif[l]
                    # dNH4[l] = dNH4[l] + m_dDNitrif[l]
                    NO3ToNH4_1 = NO3ToNH4_1 + m_dDNitrif[l] * (dBD[l] * Layer[l] * 0.1)
            NO3ToNH4 = NO3ToNH4 + NO3ToNH4_1
####################### 计算氨挥发损失 ########################
            FldNH3Vloss = 0
            Kv = 0.05
            m_volatFT = 0.4 * (25.41 - 10) / 10
            m_voltFH = math.pow(10, (dPH[0] - 7.5))
            if m_FloodWH > 0:
                FLdT = 0.6 * Tmax[i] + Tmin[i] * 0.4
                FldFT = 0.41 * (FLdT - 10.0) / 10
                if FldFT > 1:
                    FLdT = 1
                if FldFT < 0:
                    FLdT = 0
                tempFldnh4 = FldNH4 * math.exp(-Kv * FldFT)
                FldNH3Vloss = FldNH4 - tempFldnh4
                if FldNH3Vloss < 0:
                    FldNH3Vloss = 0.0
                FldNH4 = tempFldnh4 # 淹水中铵态氮含量
                m_NH3loss = 0
            else:
                if dNH4[0] > 2:
                    tempdNH42 = (dNH4[0] - 0.5) * math.exp(-0.05 * min(m_volatFT, m_voltFH))
                    m_NH3loss = (dNH4[0] - 0.5) - tempdNH42
                    dNH4[0] = dNH4[0] - m_NH3loss

                else:
                    m_NH3loss = 0.0
            AllNH3loss = FldNH3Vloss + m_NH3loss
####################### 剖面土壤可供应总氮量 ########################
            TAN = 0.0 #耕层剖面可供氮量 kg/ha
            if m_FloodWH > 0:
                TAN = TAN + (FldNO3 + FldNH4 + FldUrea) * m_FloodWH * 0.1
            tempD = 0.0
            for l in range(0,10):
                tempD = tempD + Layer[l]
                if tempD <= 26:
                    dTotAN[l] = dNo3[l] + dNH4[l] + Urea[l]
                    TAN = TAN + dTotAN[l] * (dBD[l] * Layer[l] * 0.1)
                elif (tempD - Layer[l]) <=26:
                    dTotAN[l] = dNo3[l] + dNH4[l] + Urea[l]
                    TAN = TAN + dTotAN[l] * (dBD[l] * Layer[l] * 0.1) * (26 + Layer[l] - tempD) /Layer[l]
#
############植株潜在需氮量###################
            if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                NExceed = 0
                NLVExceed = 0.0  # 叶片中富余的氮量
                NSTExceed = 0.0  # 茎鞘中富余的氮量
                if PDT[i] >= 36 and  counter3 == 1:
                    GrainNCInit = max(MinGrainNC, PC/5.95 * 100 * 0.8 * m_outputFN * m_outputFN )
                    NCGN = GrainNCInit
                    # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                    ANupSO = ANupSO + ANupGN
                    counter3 = -1

                PNDEMLV = AWLVG * NCLVC[i] - ANupLV
                PNDEMTOP = ATOPWT * TCNC[i] - totANupTop
                if PDT[i] < 36:
                    # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                    PNDEMSO = AWSP * 0.018 - ANupSO
                    PNDEMGN = 0
                    NCSTC = (ATOPWT * TCNC[i] - NCLVC[i] * AWLVG - AWSP * 0.018) / WST
                    # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                    PNDEMST =  WST * NCSTC - ANupST
                    if NCSTC < 0.004:
                        NCSTC = 0.004
                        # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                        PNDEMST = WST* NCSTC - ANupST
                        PNDEMLV = PNDEMTOP - PNDEMST - PNDEMSO
                        NCLVC[i] = (ATOPWT * TCNC[i] - NCSTC * WST - AWSP * 0.018) / AWLVG
                else:  #籽粒潜在需氮量计算   // 还需要加入水分与氮素状况影响因子
                    RGPNFILL = 4.829666 - 3.95 * DTTList[i] + 0.75 * (Tmax[i] - Tmin[i]) + 5.3067 * dTmean[i]
                    RGPNFILL = RGPNFILL * SGP
                    # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                    PNDEMGN = max((dGrainNum * RGPNFILL / 100 / 1000), 0.0)
                    #考虑子粒含氮量大于上限值，取为品种含氮量GrainPC/5.95 * 1.15；
                    if NCGN >= MaxGrainNC:
                        # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                        PNDEMGN = PNDEMGN * 0.05
                    PNDEMSO = 0.0
                    # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                    PNDEMST = PNDEMTOP - PNDEMGN - PNDEMLV
                    NCSTC = (ANupST + PNDEMST) / WST
                    if NCSTC <0.004:
                        NCSTC = 0.004
                        # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                        PNDEMST = 0
                        NDEMGN = PNDEMTOP - PNDEMLV
                if PDT[i] < 36 and PDT[i] > 35:
                    totANupTop = totANupTop
                if PDT[i] < 26 and PDT[i] > 25:
                    totANupTop = totANupTop

                if PNDEMLV < 0:
                    NLVExceed = PNDEMLV
                    PNDEMLV = 0.0
                if PNDEMST < 0:
                    NSTExceed = PNDEMST
                    PNDEMST = 0.0
                NExceed = NLVExceed + NSTExceed
                PNDEMTOP2 = PNDEMLV + PNDEMST + PNDEMSO + PNDEMGN
                PNDEMTOP1 = PNDEMTOP2 + NExceed
    #############根潜在需氮量###################
                # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                PNDEMRT = AROOTWT * NCRTC[i] - totANupRT
                if PNDEMRT <= 0:
                    PNDEMRT = 0.0
                TPNDEM1 = PNDEMTOP1 + PNDEMRT #总的氮需求计算器官氮含量
                # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                TPNDEM = PNDEMTOP + PNDEMRT #总的氮需求
                if TPNDEM <=0:
                    if ATOPWT > 0:
                        NCTop = totANupTop / ATOPWT *100
                        if PDT[i] < 36:
                            ANupGN = ANupGN+0
                            ANupSO = ANupSO+0
                            ANupLV = ANupLV+0
                            ANupST = ANupST+0
                        else:
                            # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                            Ntop = NLVExceed + NSTExceed
                            ANupGN += -Ntop
                            ANupSO += -Ntop
                            ANupLV += NLVExceed
                            ANupST += NSTExceed

                        totANupTop = ANupSO + ANupST + ANupLV
                        NCLV =  ANupLV / AWLVG * 100
                        NCST = ANupST / WST * 100
                        if AWSP <=0:
                            NCSO = 0.0
                        else:
                            NCSO =  ANupSO / AWSP * 100
                        if GRAINWT <= 0:
                            NCGN = 0.0
                        else:
                            NCGN = ANupGN / GRAINWT * 100
                        if NCLV <0.009:
                            NCLV = 0.009
                        if NCST <0.0056:
                            NCST = 0.0056
                        NCTop =  totANupTop / ATOPWT * 100
                        NCRoot = totANupRT / AROOTWT * 100
                    TPNDEM = 0.0
    #############植株实际吸氮量#############
                FNH4 = [0,0,0,0,0,0,0,0,0,0]  # 铵态氮浓度影响因子
                FNO3 = [0,0,0,0,0,0,0,0,0,0]  # 硝态氮浓度影响因子
                dRootPNH4up = [0,0,0,0,0,0,0,0,0,0]
                dRootPNO3up = [0,0,0,0,0,0,0,0,0,0]
                totRootPNup = 0.0  # 根潜在吸氮能力
                for l in range(0, 10):
                    FNH4[l] = 1 - math.exp(-0.03 * (dNH4[l] - 0.5))
                    FNO3[l] = 1 - math.exp(-0.03 * (dNo3[l]))  # dNO3计算出了问题

                    if FNH4[l] < 0.01:
                        FNH4[l] = 0.0
                    if FNH4[l] > 1:
                        FNH4[l] = 1.0
                    if FNO3[l] < 0.01:
                        FNO3[l] = 0.0
                    if FNO3[l] > 1:
                        FNO3[l] = 1.0
                    WFactRootNup = (sw[l] - ll[l]) / (dul[l] - ll[l])  # 水分对根吸收影响因子
                    if WFactRootNup < 0:
                        WFactRootNup = 0.0
                    if WFactRootNup > 1:
                        WFactRootNup = 1.0
                    if m_FloodWH > 0:
                        WFactRootNup = 1.0
                    if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                        RootFacNup = dRLV[l] * WFactRootNup * WFactRootNup * 100 * Layer[l]
                    if PDT[i]>= 32 and PDT[i]<57 :
                        RootFacNup = RootFacNup * math.pow((57 - PDT[i]) / (57 - 32), 1.5)
                    if PDT[i]>57:
                        RootFacNup = RootFacNup * math.pow(0 / (57 - 32), 1.5)
                    if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                        dRootPNO3up[l] = RootFacNup * FNO3[l] * RAR * 0.001  # kg/ha /0.06单位根长的潜在吸收速率
                        dRootPNH4up[l] = RootFacNup * FNH4[l] * RAR * 0.001
                        totRootPNup = totRootPNup + dRootPNO3up[l] + dRootPNH4up[l]  # 计算根系潜在吸氮能力
    ################水层供氮量#######################
                Fld_NO3U = 0.0
                Fld_NH4U = 0.0
                if m_FloodWH > 0 and dRLV[0] > 0:
                    Fld_FNH4 = 1.0 - math.exp(-0.030 * (FldNH4 * 10 / m_FloodWH))
                    Fld_FNO3 = 1.0 - math.exp(-0.030 * (FldNO3 * 10 / m_FloodWH))
                    if Fld_FNH4 < 0.03:
                        Fld_FNH4 = 0
                    if Fld_FNH4 > 1.0:
                        Fld_FNH4 = 1.0
                    if Fld_FNO3 < 0.03:
                        Fld_FNO3 = 0
                    if Fld_FNO3 > 1.0:
                        Fld_FNO3 = 1.0
                    # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                    RootFacNup = 0.005 * dRLV[0] * m_FloodWH
                    Fld_NO3U = RootFacNup * Fld_FNO3 * RAR*0.001
                    Fld_NH4U = RootFacNup * Fld_FNH4 * RAR*0.001
                    totRootPNup += Fld_NO3U + Fld_NH4U
    ######################## 植株N需供比nuf----植株潜在需氮量/根系潜在吸氮能力 ########################
                if totRootPNup==0:
                    nuf = 0
                elif TPNDEM > totRootPNup:
                    nuf =1
                else:
                    if TPNDEM <= 0:
                        TPNDEM = 0
                        nuf = 0
                    else:
                        nuf = TPNDEM / totRootPNup

    ####################### 每日实际吸氮量dTotNuptake ########################
                dANUPNH4 = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                dANUPNO3 = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,0.0]  # 问题2017/04/23
                dANUP = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                dTotNuptake = 0.0  # 每日实际吸氮量
                totRLV = 0
                tTrootNH4 = 0
                tTrootNO3 = 0
                for l in range(0, 10):
                    dANUPNH4[l] = dRootPNH4up[l] * nuf
                    dANUPNO3[l] = dRootPNO3up[l] * nuf  # dRootPNO3up 出问题 2017/04/23
                    tempdANUPNO3 = (dNo3[l] - 0.25) * (dBD[l] * Layer[l] * 0.1)
                    if tempdANUPNO3 < 0:
                        tempdANUPNO3 = 0.0
                    if dANUPNO3[l] > tempdANUPNO3:
                        dANUPNO3[l] = tempdANUPNO3
                    tempdANUPNH4 = (dNH4[l] - 0.5) * (dBD[l] * Layer[l] * 0.1)
                    if tempdANUPNH4 < 0:
                        tempdANUPNH4 = 0.0
                    if dANUPNH4[l] > tempdANUPNH4 + 0.1:
                        dANUPNH4[l] = tempdANUPNH4
                    # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                    dTotNuptake = dTotNuptake + dANUPNH4[l] + dANUPNO3[l]  # 每日实际吸氮量
                    dNH4[l] = dNH4[l] - (dANUPNH4[l] /  (dBD[l] * Layer[l] * 0.1))
                    if dNH4[l] < 0:
                        dNH4[l] = 0
                    dNo3[l] =  dNo3[l] - (dANUPNO3[l] / (dBD[l] * Layer[l] * 0.1))
                    if dNo3[l] < 0:
                        dNo3[l] = 0
                    if dRLV[l] > 0:
                        tTrootNH4 = tTrootNH4 + dNH4[l]*(dBD[l] * Layer[l] * 0.1)
                        tTrootNO3 = tTrootNO3 + dNo3[l] * (dBD[l] * Layer[l] * 0.1)
                    totRLV = totRLV + dRLV[l]
                if (m_FloodWH > 0) and (dRLV[0] > 1.0):
                    FldNH4U = Fld_NH4U * nuf
                    FldNO3U = Fld_NO3U * nuf
                    if FldNH4U > FldNH4:
                        FldNH4U = FldNH4
                    if FldNO3U > FldNO3:
                        FldNO3U = FldNO3
                    dTotNuptake += FldNH4U + FldNO3U
                    FldNH4 = FldNH4 - FldNH4U
                    FldNO3 = FldNO3 - FldNO3U
    ######################## 地 上/下 部氮积累量 ########################
                TempTopNUP = 0
                if PNDEMTOP < 0:
                    PNDEMTOP = 0
                if TPNDEM <= 0 or dTotNuptake <= 0:
                    totANupTop = totANupTop + 0.0
                    totANupRT =  totANupRT + 0.0
                else:
                    if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                        totANupTop = totANupTop + PNDEMTOP / TPNDEM * dTotNuptake
                        totANupRT = totANupRT +  PNDEMRT / TPNDEM * dTotNuptake
                        TempTopNUP =  PNDEMTOP / TPNDEM * dTotNuptake
                # if GDD[i] > TrplGDD and counter5 == 1:
                #     totANupTop =totANupTop/0.2469
                #     totANupRT = totANupRT/0.2469
                #     counter5 = -1
                totANup = totANupTop + totANupRT
                NCTop = totANupTop / ATOPWT * 100
    ########氮素在各个器官的分配 ############
                NRMLV = 0.0 #叶片最大可转运氮量
                NRMST = 0.0
                NRMRT = 0.0
                NCLVmin = max(NCLVC[i] * 0.7, 0.014)
                NCSTmin = max(NCSTC * 0.3, 0.004)
                NCRTmin = max(NCRTC[i] * 0.8, 0.009)
                NGROGNR = 0
                TNDEMLVSTExceed = PNDEMLV + PNDEMST + NSTExceed + NLVExceed
                NR = totANupTop / (ATOPWT * TCNC[i])
                NTR = 0 #转移数量
                if TPNDEM > 0:
                    if PDT[i] < 36:
                        # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                        ANupLV = NR * (AWLVG * NCLVC[i])
                        ANupSO = NR * (AWSP * 0.018)
                        ANupST = totANupTop - ANupLV - ANupSO
                        ANupGN = 0
                    else:
                        if PNDEMGN <= (TempTopNUP - NExceed):
                            NGROGNR = PNDEMGN
                            TempTopNUP = TempTopNUP - NExceed - PNDEMGN #籽粒氮需求满足后剩余氮
                            TNDEMLVST = PNDEMLV + PNDEMST
                            # if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                            if TNDEMLVST == 0:
                                ANupLV = ANupLV + NLVExceed + TempTopNUP * NSTExceed / NExceed
                                ANupST = ANupST + NSTExceed + TempTopNUP * NLVExceed / NExceed
                            else:
                                ANupLV = ANupLV + NLVExceed + TempTopNUP * PNDEMLV / TNDEMLVST
                                ANupST = ANupST + NSTExceed + TempTopNUP * PNDEMST / TNDEMLVST
                            NRMLV = 0
                            NRMST = 0
                            NRMRT = 0
                        else:
                            if NLVExceed < 0:
                                NCLV = NCLVC[i] * 100
                            if NSTExceed < 0:
                                NCST = NCSTC * 100
                            NRMLV = max(AWLVG * (NCLV * 0.01 - NCLVmin), 0)
                            NRMST = max(WST * (NCST * 0.01 - NCSTmin), 0)
                            NRMRT = max(AROOTWT * (NCRoot * 0.01 - NCRTmin), 0)
                            NRMTOP = NRMLV + NRMST
                            PNDEMGN = PNDEMGN - (TempTopNUP - NExceed)
                            duf = (NRMTOP + NRMRT) / PNDEMGN
                            if duf < 1:
                                PNDEMGN = PNDEMGN * duf
                            if PNDEMGN <= NRMTOP:
                                if NRMTOP != 0:
                                    NRMLV = min(PNDEMGN * NRMLV / NRMTOP, NRMLV)
                                    NRMST =min(PNDEMGN * NRMST / NRMTOP, NRMST)
                                    NRMRT = 0.0
                            else:
                                NRMRT = 0
                            NGROGNR = TempTopNUP - NExceed + NRMLV + NRMST + NRMRT
                            if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                                ANupLV = ANupLV + NLVExceed - NRMLV
                                ANupST = ANupST + NSTExceed - NRMST
                        if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                            ANupGN = ANupGN + NGROGNR
                            ANupSO = ANupSO + NGROGNR
                    NCLV = ANupLV / AWLVG * 100
                    if NCLV < NCLVmin:
                        NCLV = 0.009
                    NCST = ANupST / WST * 100
                    if NCST < NCSTmin:
                        NCST = 0.100
                    if AWSP<=0:
                        NCSO = 0.0
                    else:
                        NCSO = ANupSO / AWSP * 100
                    if GRAINWT <=0:
                        NCGN = 0.0
                    else:
                        NCGN = ANupGN / GRAINWT * 100
                    NCRoot = totANupRT / AROOTWT * 100
                    if NCGN < 0:
                        NCGN = 0.0
                    if NCGN > 100:
                        NCGN = 0.0
                totANupTop1 = ANupSO + ANupST + ANupLV
    ######################## N素亏缺因子m_outputFN ########################
    # NDEF1影响光合作用
    # NDEF2影响叶片及籽粒含氮量
                m_outputFN = 1.0
                if PDT[i]<36 and PDT[i]>35:
                    totANupTop = totANupTop * 1
                if NCTop/100 <= TNCL[i]:
                    LimitN = TNCL[i]
                elif NCTop/100 <= TCNC[i]:
                    LimitN = NCTop / 100
                else:
                    LimitN = TCNC[i]
                m_outputFN = (LimitN - TNCL[i]) / (TCNC[i] - TNCL[i])
                if PDT[i] < 57 and PDT[i]> 56:
                    NCTop = NCTop * 1
                if GDD[i] <=TrplGDD :
                    m_outputFN = 1
                NDEF1 = math.pow(m_outputFN, 0.5) # 对光合
                NDEF2 = math.pow(m_outputFN, 0.5)
                if NDEF1 < 0.01:
                    NDEF1 = 0.01
                if NDEF1 > 1:
                    NDEF1 = 1.0
                if NDEF2 < 0.01:
                    NDEF2 = 0.01
                if NDEF2 > 1:
                    NDEF2 = 1.0

            if counter1 == 1:
                dTNUMTILLER = 1.0 * PLANTS/Diluted
                LAI = ABIOMASS * 1000 * 1000 * 0.00013 / (TGW * 10000)
                AWLVG1 = LAI / 450 * 10000 * 10  # 实际绿叶重
                WST1 = AWLVG1 / 0.54 * 0.46  # 茎鞘重
                ATOPWT1 = AWLVG1 + WST + WSP  # 地上部
                AROOTWT1 = AWLVG1 / 0.54 / 0.63 * 0.37  # 根重
                ABIOMASS1 = WST1 + AWLVG1 + AROOTWT1
                dGRT = AROOTWT
                AWLVG = 0
                AWSP = 0
                WST = 0
                PDT0 = PDT[i] #存储第出苗时PDT
                # ##############氮素模块############

                # totANupTop = ANupLV + ANupST
                # totANupRT = 1 * 0.07 * 0.35
                # totANup = totANupTop + totANupRT

            #################################
                counter1 = -1
            if GDD[i] > TrplGDD and counter4 == 1:
                LAI = LAI/Diluted   # LAI/0.2469
                LAI1 = LAI
                AWLVG = AWLVG/Diluted
                ABIOMASS1 = ABIOMASS1/Diluted # ABIOMASS1/0.2469
                #     AWLVG = AWLVG / Diluted
                WST = WST/Diluted
                ATOPWT = ATOPWT/Diluted
                AROOTWT = AROOTWT/Diluted *0.8
                ANupGN = ANupGN /Diluted
                ANupLV = ANupLV/Diluted
                ANupST = ANupST/Diluted
                ANupSO = ANupSO/Diluted
                totANupTop =totANupTop/Diluted
                totANupRT = totANupRT/Diluted
                dGrainNum =dGrainNum/Diluted
                GRAINWT = GRAINWT/Diluted
                # dTNUMTILLER = dTNUMTILLER/Diluted
                # dGRT = 0

                dTotNuptake = 0
                totRootPNup = 0
                # TPNDEM = 0
                # PNDEMTOP = 0
                # PNDEMRT = 0
                PNDEMST  = 0
                PNDEMLV = 0.0
                counter4 = -1
################### 每日总同化量SumDTGA----RicePhotoBiomassModel----P149 ########################
            else:
                if PDT[i] > PDT0:
                    DTGA = 0.0 #每日冠层光合作用速率
                    for j in range(0,3):
                        SumTPS_j = 0.0
                        for k in range(0, 5):
                            LGUSS_k = DIS5[k] * LAI  # 冠层第 k 层的叶面积指数
                            Il_j_k = (1 - p_j[i][j]) * PAR_i[i][j] * math.pow(math.e, (-K_j[i][j] * LGUSS_k))  # 第 j 个时刻太阳辐射在小麦冠层第 k 层的分布
                            Ila_j_k = Il_j_k * K_j[i][j] #第 j 个时刻在冠层 k 的吸收辐射量
                            if AMAX[i]*min(m_outputSWDF1, m_outputFN) != 0:
                                PS_j_k = AMAX[i]*min(m_outputSWDF1, m_outputFN) * (1 - math.exp(-0.48 * Ila_j_k /( AMAX[i] * min(m_outputSWDF1, m_outputFN)) ))
                            else:
                                PS_j_k = AMAX[i]*min(m_outputSWDF1, m_outputFN) * (1 - math.exp(-0.48 * Ila_j_k / 1))
                            TPS_j_k = PS_j_k * WGUSS5[k]
                            SumTPS_j = SumTPS_j + TPS_j_k
                        TPS_j = SumTPS_j * LAI
                        # TPS_j = SumTPS_j * 0.46
                        DTGA_j = TPS_j * WGUSS3[j]
                        DTGA = DTGA + DTGA_j
                    DTGA = DTGA * DL[i] * 0.682 # 当天光合同化量
        ################################## 生长呼吸速率RG----RicePhotoBiomassModel----P177 ##########################################
                    RG = RGC * DTGA #生长呼吸速率
        ################################## 标准参照温度T0时的维持呼吸RMT0----RicePhotoBiomassModel----P179 ##########################################
                    RMT0 = 0.008 * AWLVG + 0.004 * WST + 0.008 * AROOTWT + 0.015 * AWSP
        ########################################## 维持呼吸消耗量RM ##########################################
                    temp1 = (T24H[i] - 25.0) / 10.0
                    RM = RMT0 * math.pow(2, temp1)
        ######################### 日干物质积累W----RicePhotoBiomassModel----P183 ########################
                    W = (DTGA - RM - RG) / 0.95
    ######################### 总干物质积累W----RICEInfo----P706 ########################
                    TOPWTi = ABIOMASS1 * PIS[i-1]
                    WSTi = ABIOMASS1 -AWLVG - AWSP
                    if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                        ABIOMASS1 = ABIOMASS1 + W
    ##########################################    物质分配    #########################################################################
                TOPWT = ABIOMASS1 * PIS[i] #潜在地上部分配
                dTOPWT = (TOPWT - ATOPWT) * m_outputSWDF2 #地上部分每日增加量
                WLVGpi =  ATOPWT * PILVG[i-1] #昨日潜在绿叶生物量
                WSPpi = ATOPWT * PISP[i-1] #昨日潜在穗生物量
                ATOPWT = ATOPWT + (TOPWT - ATOPWT) * m_outputSWDF2 #实际地上部分配(只考虑水分对地上地下部干物质分配的影响)
                WLVG = ATOPWT * PILVG[i] #潜在绿叶
                WSP = ATOPWT * PISP[i] #潜在穗
                if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                    AROOTWT = ABIOMASS1 - ATOPWT #实际地下部分分配
                    dGRT = AROOTWT - AROOTWTSeq[i-1]
                FShoot = ATOPWT / ABIOMASS1
    ######### 实际绿叶重AWLVG----RiceTopRootModel----P83 ########################
                if 13 < PDT[i] <= 57:
                    if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                        dWLVG = (AWLVG / ATOPWT / PILVG[i]) * (WLVG - WLVGpi) * min(m_outputSWDF2, m_outputFN) # 叶每日增加量
                        AWLVG = AWLVG + (AWLVG / ATOPWT / PILVG[i]) * (WLVG - WLVGpi) * min(m_outputSWDF2, m_outputFN)
                else:
                    if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                        dWLVG = (WLVG - WLVGpi) * min(m_outputSWDF2, m_outputFN) # 叶每日增加量
                        AWLVG = AWLVG + (WLVG - WLVGpi) * min(m_outputSWDF2, m_outputFN)
    ######################## 实际穗重WSP----RiceTopRootModel----P84 ######################
    ######### 计算不利高温、低温对结实率的影响 ########
                LowTempSum = 0.0
                if 26 <= PDT[i] <= 39 and T24H[i] < 22:
                    LowTempSum = LowTempSum + (22 - T24H[i])
                    FT = 1 - (4.6 + 0.054 * math.pow(LowTempSum, 1.56)) / 100  #低温
                elif 32 <= PDT[i] <= 39 and Tmax[i] > 36.6:
                    FT = 1 / (1 + math.exp(0.853 * (Tmax[i] - 36.6)))  # 低温
                else:
                    FT = 1
                dGSO = (WSP - WSPpi)  * FT #穗每日增加量
                if dGSO < 0:
                    dGSO = 0
                AWSP = AWSP + dGSO
    ######################## 实际茎鞘WST----RiceTopRootModel----P84 ########################
                dGST = dTOPWT - dWLVG - dGSO
                WST = ATOPWT - AWLVG - AWSP
    ######################## 叶面积指数LAI----RiceTopRootModel----P105 #######################
                if GDD[i] > TrplShockGDD:
                    TempGDD = GDD[i] - TrplShockGDD
                else:
                    TempGDD = GDD[i] - EMGDD

                if LAI < 1.6 and PDT[i] <= 34:
                    # rp = max(LRS, 0.0045)
                    if LRS < 0.0045:
                        rp = 0.0045
                    else:
                        rp = LRS
                    if GDD[i] > TrplShockGDD:
                        LAI = LAI1 * math.exp(rp * TempGDD)
                    elif GDD[i] <= TrplGDD:
                        LAI = (ABIOMASS * 1000 *1000 * 0.00013 / (TGW * 10000)) * math.exp(rp * TempGDD)
                    else:
                        LAI = LAI

                    if LAI > 1.6:
                        LAI = 1.6

                elif LAI >= 1.6 and PDT[i] < 34:
                    dLAI2 = AWLVG * SLA[i] *0.0001 * 0.1
                    if dLAI2 <= 1.6:
                        LAI = 1.6
                    else:
                        LAI = dLAI2
                elif LAI <= 1.6 and PDT[i] >= 34:
                    LAI = AWLVG * SLA[i] * 0.0001 * 0.1
                elif LAI > 1.6 and PDT[i] > 34:
                    LAI = AWLVG * SLA[i] * 0.0001 * 0.1
                if LAI > 10:
                    LAI = 10
    ######################## 同化物供应状况TOPSF----RiceTopRootModel----P152 ########################
                YIELD = AWSP * 0.87

    ######################## 叶龄计算----RiceTopRootModel----P152 ########################
                a = 0.0428  # 原为 0.0428
                b = 0.7718# 原为 0.7883，依据同上修改为 0.7718
                if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                    dLN = a * math.pow(TTSlist[i], b)  # 主茎叶龄
                if dLN >= TLN + 1:
                    dLN = TLN + 1
    ######################## 叶面积指数对茎蘖的影响因子----RiceTopRootModel----P152 ########################
                LAIF = 0.0  # 叶面积指数对茎蘖的影响因子
                LAIC = 4.5  # 分蘖停止时的 LAI 阈值

                if LAI <= 1.6:
                    LAIF = 1.0
                elif LAI <= LAIC:
                    LAIF = 18.91 * math.exp(-1.84 * LAI)
                else:
                    LAIF = 0

                if dLN < 4:
                    dTNUMTILLER = 1.0 * PLANTS/Diluted
                elif dLN >= 4 and dLN <= (TLN - EIN + 2):

                    DTillerNum = 0.04811 * math.exp(0.3654 * (dLN - 4 + 1)) * PLANTS/Diluted
                    if GDD[i] > TrplShockGDD:
                        dTNUMTILLER = dTNUMTILLER + DTillerNum * TA *0.1 * LAIF * min(m_outputSWDF2, m_outputFN)  # 群体茎蘖实际增长量（万/ha）
                    elif GDD[i] <= TrplGDD:
                        dTNUMTILLER = dTNUMTILLER + DTillerNum * TA *0.1 * LAIF * min(m_outputSWDF2, m_outputFN)  # 群体茎蘖实际增长量（万/ha）
                    else:
                        dTNUMTILLER = dTNUMTILLER


                    if dTNUMTILLER > (TILLPOPMAX * TA *0.1 ):
                        dTNUMTILLER = TILLPOPMAX * TA *0.1
                else:
                    dTNUMTILLER = dTNUMTILLER
    ################以下计算有效分蘖可靠叶龄期的茎蘖数######################
                LNE = TLN - EIN  # 有效分蘖临界期
                LNJ = TLN - EIN + 3 # 拔节叶龄     停止分蘖时的叶龄为LNMAX - N + 2
                if dLN >= LNE and not Flag1:
                    TILLPOPE = dTNUMTILLER  # 有效分蘖数（万/ha），3张叶片及以上茎蘖数
                    Flag1 = True
                if dLN >= LNJ and not Flag2:
                    TrillerJNum = dTNUMTILLER
                    Flag2 = True
                # else:
                #     TrillerJNum = 0.0
    ################以下计算拔节后的茎蘖动态 衰减与消亡######################
                if dLN > (TLN - EIN +2) and dLN < (TLN - EIN +3):
                    dPTNUMTILLER = 0.3811 * math.exp(0.2654 * (dLN - 4 + 1)) * PLANTS/Diluted  # 改为 0.3811 原为 0.03811
                    dTNUMTILLER = dTNUMTILLER + dPTNUMTILLER * TA *0.1  * LAIF * min(m_outputSWDF2, m_outputFN)  # 群体茎蘖的实际增长量（万/ha）
                elif dLN >= (TLN - EIN + 3) and dLN < TLN + 1:  # +1 为抽穗期开始时的叶龄
                    JPDT = 32 - 3.2 * EIN
                    dTNUMTILLER = dTNUMTILLER - FShoot * DPElist[i] * (TrillerJNum - TILLPOPE) / (32 - JPDT)
                elif dLN >= TLN + 1:
                    dTNUMTILLER = dTNUMTILLER

    ####################计算籽粒数与籽粒重##############################
    ###########籽粒数################
                if PDT[i] >= 26 and not Flag3:
                    WSTMIN = WST
                    Flag3 = True
                else:
                    WSTMIN = 0.0
                if PDT[i] < 28:     # 孕穗28
                    dGrainNum = 0.0
                if PDT[i] >=28 and PDT[i] <=39:  #  孕穗 -- 灌浆始期
                    if dGrainNum == 0.0:
                        dGrainNum = (AWSP + WST) * 0.5 * 100 * 1000 / 10000  # 万 / ha其中，0.5 * 100 = 50为每克碳水化合物所能形成籽粒的数量，*1000 为kg / ha * 1000 = g / ha, / 10000则为粒数 / 10000 = 万粒，最终单位：万 / ha
                    dGrainNum = dGrainNum + (dGSO / FT + dGST) * 0.5 * 100 * 1000 / 10000 * FT   #万/ha  dGSO-穗的生物量 dGST-当日穗重变化 FT-温度对结实率的影响
    #############籽粒重###################
                if PDT[i] > 36:
                    if not Flag4:
                        GRAINWTi = GRAINWTi + PerGrainInit / 1000 * 0.001 * dGrainNum * 10000 # 籽粒重 = 前一天重 + 单粒重 / 1000 * 籽粒数 * 0.001 * 10000单粒重 / 1000 * 0.001为（mg / 粒） / 1000 * 0.001 = kg / 粒，dGrainNum * 10000 =（万 / ha）*1000 = 粒 / ha。最终单位kg / ha
                        Flag4 = True
                    grainFillRate = TGW / 1000 / (57 - 36) # THGRAINW - 千粒重粒重 / 灌浆期PDT之差
                    if PDT[i] < 41:
                        grainFillRate = grainFillRate * 0.7059 # longer1202006.10 .23最快速灌浆期速率是最低时期的2倍与3倍
                    elif PDT[i] <= 51:
                        grainFillRate = grainFillRate * 1.4118
                    else:
                        grainFillRate = grainFillRate * 0.4706 * (1.5 - 0.2 * (PDT[i] - 51))
                    dGrainNC = NCGN
                    GrainPC = PC * 100
                    if dGrainNC <= 0.85:
                        grainFillRate = 0
                    if (dGrainNC > 0.85) and dGrainNC < (GrainPC / 5.95 * 0.7):
                        grainFillRate = grainFillRate * (dGrainNC - 0.85) / (GrainPC / 5.95 * 0.7 - 0.85)
                    TMPF = 1.0
                    if dTmean[i] < 16 or dTmean[i] > 40:
                        TMPF = 0.0
                    if dTmean[i] > 29 or dTmean[i] <= 40:
                        TMPF = math.sin((40 - dTmean[i]) / (40 - 29) * math.pi / 2)
                    if dTmean[i] >= 16 or dTmean[i] < 24:
                        TMPF = math.sin((dTmean[i] - 16) / (24 - 16) * math.pi / 2)
                    PGRAINWTDEM = DPElist[i] * grainFillRate * dGrainNum * TMPF * 0.001 * 10000 #籽粒日灌浆碳需求
                    dDTOPWT = (TOPWT - TOPWTi) * m_outputSWDF2
                    dGCPhotos = dDTOPWT
                    if PGRAINWTDEM <= dGSO:
                        dGGRAINWT = PGRAINWTDEM
                    else:
                        duf = 1.0
                        if PGRAINWTDEM <= dGCPhotos:
                            if dWLVG > 0:
                                dWLVG = 0.0
                            dWLVG = dWLVG * duf
                            dGST = dGCPhotos - PGRAINWTDEM + dWLVG
                            dGGRAINWT = PGRAINWTDEM
                        else:
                            dGGN = PGRAINWTDEM - dGCPhotos
                            if dGST >= 0:
                                dGST = 0.0
                            else:
                                dGST = max(dGST, -(WSTi - WSTMIN))
                                if WSTi < WSTMIN:
                                    dGST = 0
                            if dWLVG > 0:
                                dWLVG = 0.0
                            dGCTrans = math.fabs(dGST + dWLVG)
                            TempDGN = dGGN - dGCTrans
                            if TempDGN <= 0:
                                duf = dGGN / dGCTrans
                                if dGST < 0:
                                    duf = dGGN / dGCTrans
                                    dWLVG = dWLVG * duf
                                    dGST = dGST * duf
                                else:
                                    dTempGST = min(TempDGN, (WSTi - WSTMIN))
                                    if WSTi < WSTMIN:
                                        dTempGST = 0
                                    dGST = dGST - dTempGST
                                    dGGRAINWT = dGCPhotos - dWLVG - dGST
                    if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                        GRAINWT = GRAINWTi + dGGRAINWT
                    PerGrainW = GRAINWT / dGrainNum * 0.1
    ######################## RootModel----RiceTopRootModel----P292 ########################
    ######################## RootModel数据初始化 ########################
            RLNEW = dGRT * 1.05  # 每日新生长的根长
            SWDF1 = 1.0  # 土壤水分影响因子
            GRTDEP = 0.03 * DTTList[i] * SWDF1
            if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                dRTDEP = dRTDEP + GRTDEP
            if dRTDEP > 50:
                dRTDEP = 50
            cumdep = 0.0
            TRLDF = 0.0
            tempCount = 0
            for l in range(0,10):
                tempCount = tempCount+1
                cumdep = cumdep +Layer[l]
                dMidDepth = cumdep - Layer[l] / 2
                dTEMPSWDF = M_DSWDF[l]
                RLDF[l] = WR[l] * dTEMPSWDF * Layer[l]
                if cumdep >= dRTDEP:
                    RLDF[l] = RLDF[l] * (1 - (cumdep - dRTDEP) / (Layer[l] + 0.01))
                    TRLDF = TRLDF + RLDF[l]
                    break
                TRLDF = TRLDF + RLDF[l]
            cumdep = 0
            RNLF = RLNEW / TRLDF
            tempCount = 10
            if TRLDF == 0:
                TRLDF = 1.0
            if GDD[i] <= TrplGDD or GDD[i] > TrplShockGDD:
                for l in range(0,10):
                    tempRLV = 0
                    if l <=9:
                        cumdep = cumdep + Layer[l]
                        if TRLDF == 0:
                            TRLDF = 1
                        tempRLV =dRLV[l] + (RLDF[l] * RNLF / Layer[l]) - 0.01 * dRLV[l]
                        if tempRLV < 0:
                            tempRLV = 0
                        if cumdep > 50:
                            rlvf = 0.377 - 0.0015 * cumdep
                            if tempRLV > rlvf:
                                tempRLV = rlvf
                    dRLV[l] = tempRLV

            #############################################################################################
                    # if PDT[i] == 57:
                    #
                    #     dTNUMTILLERSeq.append(dTNUMTILLER)  # 茎蘖总数
                    #     YIELDSeq.append(YIELD)
                    #     dGrainNumSeq.append(dGrainNum)

        aAWLVG = AWLVG + 0
        aWST = WST + 0
        aAROOTWT = AROOTWT + 0
        aWSP = AWSP + 0   # 穗重
        aYIELD = YIELD + 0  # 籽粒产量
        # aABIOMASS = ABIOMASS + 0
        AWLVGSeq.append(aAWLVG)
        WSTSeq.append(aWST)
        AROOTWTSeq.append(aAROOTWT) # 根重
        WSPSeq.append(aWSP) 
        YIELDSeq.append(aYIELD) 
        dTNUMTILLERSeq.append(dTNUMTILLER)
        dLNSeq.append(dLN)
        dGrainNumSeq.append(dGrainNum)
        LAISeq.append(LAI)
        ABIOMASSSeq.append(ABIOMASS1) # 总 biomass
        ATOPWTSeq.append(ATOPWT) # 顶部 biomass
        dGrainNumSeq.append(dGrainNum)
        m_outputFNSeq.append(m_outputFN) # 每日输出氮量
        NCTopSeq.append(NCTop) 
        totANupTopSeq.append(totANupTop)  #
        TPNDEMSeq.append(TPNDEM)
        PNDEMTOPSeq.append(PNDEMTOP)
        dTotNuptakeSeq.append(dTotNuptake)#每日实际吸氮量
        RootFacNupSeq.append(RootFacNup)
        m_outputSWDF2Seq.append(m_outputSWDF2)
        SoilTempratureSeq.append(SoilTemprature) # 土壤温度
        totRootPNupSeq.append(totRootPNup)  # 总根氮 uptake
        WFactRootNupSeq.append(WFactRootNup) 
        dTotRLVSeq.append(dTotRLV)
        m_FloodWHSeq.append(m_FloodWH)
        m_outputSWDF1Seq.append(m_outputSWDF1)
        GRAINWTSeq.append(GRAINWT)
        dRTDEPSeq.append(dRTDEP)
        UreaSeq.append(Urea[0])
        dRLVSeq.append(dRLV[0])
        RLDFSeq.append(RLDF[0])
        RLNEWSeq.append( RLNEW)
        ANupLVSeq.append(ANupLV)
        dGRTSeq.append(RootFacNup)
        FldUreaSeq.append( FldUrea)
        FldNO3Seq.append(FldNO3) 
        FldNH4Seq.append(FldNH4) 
        PNDEMRTSeq.append(PNDEMRT)
        dRootPNO3upSeq.append(dRootPNO3up[0]) 
        dRootPNH4upSeq.append(dRootPNH4up[0]) 
        dANUPNO3Seq.append(dANUPNO3[0])
        FOMSeq.append(FOMpool[0][0]) 
        FNH4Seq.append(FNH4[0])
        m_KHFTSeq.append(m_KHFT)

    return AROOTWTSeq,AWLVGSeq,WSTSeq,WSPSeq,ATOPWTSeq,LAISeq,dTNUMTILLERSeq,YIELDSeq,dTotNuptakeSeq







def CalFun(FieldPath,WeatherPath,SoilFieldPath,ResiduePath,PlantingPath,CultivarPath,FertilizerPath):
    listBlock = []
    Cx =GetCO2(WeatherPath)
    # Cx = 486  # 二氧化碳浓度
################## 取数据 ##################
    LAT = GetLAT(FieldPath)
    Site = GetSite(FieldPath)
    SowDates = GetSowDate(FieldPath)
    TransplantDates = GetTransplantDate(FieldPath)
    WeatherDF = GetWeather(WeatherPath, SowDates, Site)
    Tmax_year = GetTmax_year(WeatherPath)
    Tmin_year = GetTmin_year(WeatherPath)
    daily_mean_temps = calc_daily_mean_temp_series(Tmax_year, Tmin_year)
    year = GetYear(WeatherPath)
    months_2024 = generate_months_for_whole_year(year)
    month_sum_temp, month_day_counter = accumulate_monthly_temp(daily_mean_temps, months_2024)
    MeanmonthTemp, MeanYearTemp, MaxMonthTemp, MinMonthTemp = calc_year_temp_stats(month_sum_temp,month_day_counter)
    # state = calc_year_temp_stats(month_sum_temp,month_day_counter)
    Tmax = GetTmax(WeatherDF)
    Tmin = GetTmin(WeatherDF)
    Precip = GetPrecip(WeatherDF)  # 降水
    TheDate = GetTheDate(WeatherDF)
    DOY = GetDOY(TheDate)
################## 品种参数 ##################
    cultivar_params_tuple = GetCultivarParams(CultivarPath)
    # 现在GetCultivarParams返回21个值，第一个是品种名称，后面是20个参数
    PZ = cultivar_params_tuple[0]  # 品种名称
    PS, TS, TO, IE, HF, FDF, PHI, SLAc, PF, AMX, KF, TGW, RGC, LRS, TLN, EIN, TA, SGP, PC, RAR = cultivar_params_tuple[1:]  # 品种参数
################## 管理措施 ##################
    ABIOMASS,plantingDepth = GetPlantSeedQuantity(PlantingPath)# kg/ha  播种量

    Diluted = GetDiluted(PlantingPath, ABIOMASS, TGW)
    DOY_list, Fertilizer_list=ReadFertilizerData(FertilizerPath)
    UREA = GetUREA(DOY,DOY_list, Fertilizer_list)  # 施尿素量及施肥日期
################## 土壤数据 ##################
    dNH40 =GetNH4(SoilFieldPath)# 铵态氮态氮含量

    dNO30 = GetdNO3(SoilFieldPath) # 硝态氮含量

    dTN0 = GetdTN(SoilFieldPath)# 全氮

    m_inputOM0 =Getm_inputOM(SoilFieldPath)# 有机质含量

    dBD =GetdBD(SoilFieldPath)# 容重

    AvedBD = CalAvedBD(dBD)  # 容重平均值
    dul =GetDUL(SoilFieldPath)# 田间持水量

    Layer = [15, 15, 15, 15, 15, 15, 15, 15, 15, 15]  # 土层厚度
    dClay = GetdClay(SoilFieldPath)# 黏粒含量

    m_dStraw = GetpreviousCropStraw(ResiduePath)

    m_dStubble = GetpreviousCropStubble(ResiduePath)

    ResidueDepth =GetresidueDepth(ResiduePath)

    FOM = [0,0,0,0,0,0,0,0,0,0] #新鲜有机质
    FON = [0,0,0,0,0,0,0,0,0,0] #新鲜有机质氮含量
    HUM = [0,0,0,0,0,0,0,0,0,0] #腐殖质
    NHUM = [0,0,0,0,0,0,0,0,0,0] #腐殖质氮含量
    FOMpool = [[0.0 for _ in range(3)] for _ in range(10)]
    dNO3out = [0,0,0,0,0,0,0,0,0,0]
    dNO3up = [0,0,0,0,0,0,0,0,0,0]
    dNH4out = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    dNH4up = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    dUreaOut= [0,0,0,0,0,0,0,0,0,0]
    dUreaUp= [0,0,0,0,0,0,0,0,0,0]
    sw0 =Getsw(SoilFieldPath)
    # sw = [0.16,0.15,0.15,0.15,0.15,0.15,0.15,0.15,0.15,0.15]  # 土层实际含水量
    NH4 = CaldNH4(dNH40)  # 土层中铵态氮含量----初始分层
    NO3 = CaldNO3(dNO30)  # 土层中硝态氮含量----初始分层

    dTN = CaldTN(dTN0)  # 土层中全氮含量----初始分层
    m_inputOM = Calm_inputOM(m_inputOM0)  # 有机质含量----初始分层
    dPH =GetdPH(SoilFieldPath)# PH值

    ll = Getll(SoilFieldPath)#萎蔫含水量

################################################
    dRLV = [0,0,0,0,0,0,0,0,0,0]  # 根毛密度
    flux = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # 每层通水量
    Urea =[0, 0, 0, 0, 0, 0, 0, 0, 0, 0]   # 土壤尿素含量
    dTotAN =NO3 + NH4 + Urea
    SMN = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # 有机氮累积矿化的标准天数
    dNO3out = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] #硝态氮淋洗量
    dNO3up = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] #硝态氮淋洗上升量
    dUreaOut = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # 尿素氮淋洗量
    dUreaUp = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # 尿素氮淋洗上升量
    dStrawMN = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # 各层秸秆分解释放氮量

#################################### RiceDevelopmentModel ####################################
    LengthTi = CalLengthTi(Tmax, Tmin)
    Ti = CalTi(LengthTi)
    Day_lengths = CalDayLong(TheDate, LAT)
    RPE,pc1 = CalRPE(PS,Day_lengths)
    PDT,GDD,EMGDD,TrplShockGDD,TTSlist,DPElist,TrplGDD,DTTSlist,DTTList = CalPDT(plantingDepth,RPE,FDF,Ti,TS,TO,IE,HF,SowDates,TransplantDates)
#################################### RiceTopRootModel ####################################
    PIS = CalPIS(PDT)
    PILVG = CalPILVG(PDT)
    PISP = CalPISP(PDT,PHI)
    SLA = CalSLA(GDD,SLAc)
#################################### RicePhotoBiomassModel ####################
    FA = CalFA(PDT,PF)
    T24H = CalT24H(Tmax, Tmin)
    FTMP = CalFTMP(T24H)
    FCO2 = CalFCO2(Cx)
    AMAX = CalAMAX(FTMP,FA,FCO2,AMX)
    DEC = CalDEC(DOY)
    SSIN = CalSSIN(LAT,DEC)
    CCOS = CalCCOS(LAT, DEC)
    SSCC = CalSSCC(SSIN,CCOS)
    DSINBE = CalDSINBE(Day_lengths, SSIN, CCOS, SSCC)
    LengthTh_j = CalLengthTh_j(Day_lengths)
    Th_j = CalTh_j(LengthTh_j)
    LengthSINB_ij = CalLengthSINB_ij(SSIN, CCOS, Th_j)
    SINB_ij = CalSINB_ij(LengthSINB_ij)
    dSunH = GetdSunH(WeatherDF)
    Q = CalQ(WeatherDF)
    LengthPAR_i = CalLengthPAR_i(Q,SINB_ij,DSINBE)
    PAR_i = CalPAR_i(LengthPAR_i)
    LengthK_j = CalLengthK_j(SINB_ij, KF, PDT)
    Lengthp_j = CalLengthp_j(SINB_ij)
    p_j = Calp_j(Lengthp_j)
    K_j = CalK_j(LengthK_j)
#################################### RiceWBalanceModel ###################################
    sat = Calsat(dBD)  # 土层饱和含水量
    KSat = CalKSat(sat, dul)  # 土层饱和导水率
    Kt = CalKt(Tmax)  # 作物蒸腾土壤蒸散的中间变量
    WF = CalWF(Layer)  # 土壤条件对径流影响
    dTmean = CaldTmean(Tmax, Tmin)  # 日均温，和CalT24H的计算方法不同，RiceNBalanceModel中也要用到
    accumSoilT = CalaccumSoilT(dTmean)
    FiveDayAveST = CalFiveDayAveST(Tmax, Tmin)
#################################### RiceNBalanceModel ####################################
    m_ntFPH = Calm_ntFPH(dPH)  # 计算硝化作用中间变量
    NCLVC = CalNCLVC(PDT) # 叶片临界含N率（KgN/Kg)
    TCNC = CalTCNC(NCLVC) ##植株临界含N率
    TNCL = CalTNCL(TCNC)  # 植株最小含N率
    NCRTC = CalNCRTC(PDT, NCLVC)  # 根临界含N率
    WR,WSUM = CalWR(Layer)  # 根系偏好因子
    WS = CalWS(ResidueDepth,Layer)
# ##############################################################################################################
    AROOTWTSeq,AWLVGSeq,WSTSeq,WSPSeq,ATOPWTSeq,LAISeq,dTNUMTILLERSeq,YIELDSeq,dTotNuptakeSeq = RiceGrowModel(DTTList,TNCL,NCRTC,TCNC,NCLVC,dTotAN,dPH,m_ntFPH,m_inputOM,HUM,NHUM,FOMpool,WSUM,WR,WS,m_dStubble,m_dStraw,FOM,FON,dUreaOut,dUreaUp,dNH4out,dNH4up,dNO3up,dNO3out,dBD,NO3,NH4,Urea,UREA,MinMonthTemp,MaxMonthTemp,MeanYearTemp,FiveDayAveST,accumSoilT,DOY,AvedBD,KSat,Layer,sat,dul,ll,sw0,Kt,dTmean,Q,dRLV,Precip,Day_lengths,PDT,TTSlist,DPElist,DTTSlist,ABIOMASS,TGW,p_j,PAR_i,K_j,AMAX,RGC,T24H,PIS,PILVG,PISP,Tmax,Tmin,LRS,TLN,EIN,TA,SGP,PC,RAR,GDD,EMGDD,TrplShockGDD,TrplGDD,SLA,FCO2,Diluted)


    return AROOTWTSeq,AWLVGSeq,WSTSeq,WSPSeq,ATOPWTSeq,LAISeq,dTNUMTILLERSeq,YIELDSeq,dTotNuptakeSeq






if __name__ == "__main__":
    # 替换CSV文件路径
    FieldPath = "调参数据.csv"
    WeatherPath = "气象数据.csv"
    SoilFieldPath = "土壤数据.csv"
    ResiduePath = "秸秆数据.csv"
    PlantingPath= "管理数据.csv"
    CultivarPath = "品种参数.csv"
    FertilizerPath = "施肥数据.csv"
    OutputPath = "模型输出.csv"
    try:

        listBlock = CalFun(FieldPath, WeatherPath,SoilFieldPath,ResiduePath,PlantingPath,CultivarPath,FertilizerPath)
        df = pd.DataFrame({
            "AROOTWTSeq": listBlock[0],
            "AWLVGSeq": listBlock[1],
            "WSTSeq": listBlock[2],
            "WSPSeq": listBlock[3],
            "ATOPWTSeq": listBlock[4],
            "LAISeq": listBlock[5],
            "dTNUMTILLERSeq": listBlock[6],
            "YIELDSeq": listBlock[7],
            "dTotNuptakeSeq": listBlock[8]
        })
        # 在最前面加一列序号
        df.insert(0, "DAYs", range(1, len(df) + 1))
        # 保存到 CSV
        df.to_csv(OutputPath, index=False, encoding="utf-8-sig")
        print(f"✅ 结果已保存到 {OutputPath}")
    except FileNotFoundError:
        print(f"Error: The file at {FieldPath} was not found.")
    except KeyError:
        print("Error: The column was not found in the CSV file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")