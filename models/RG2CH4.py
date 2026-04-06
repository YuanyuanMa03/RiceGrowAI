import numpy as np
import pandas as pd

def TemperatureIndex(Q10, t_soil):
    if t_soil > 40:
        t_sl = 30
    elif 30 <= t_soil < 40:
        t_sl = 30
    else:
        t_sl = t_soil
    TI = Q10 ** ((t_sl - 30) / 10)
    return TI

#def ShootBiomass(t, r, W0, Wmax):
    if W0 == 0:
        return np.nan
    else:
        B = Wmax / W0 - 1
        W = Wmax / (1 + B * np.exp(-r * t))
    return W

def EhvalueD(Eh, Eh0, EhR, OMND):
    result = (Eh - Eh0) * EhR * (0.23 + min(1, OMND))
    return result

def FEh(Eh):
    if Eh < -150:
        FEh = 1
    else:
        FEh = np.exp(-1.7 * (1 + Eh / 150))
    return FEh

def CH4EmissionBbl(P, t_soil, Wr):
    if Wr == 0:
        Ebl = 0.7 * P
    else:
        if t_soil > 0:
            Ebl = min(0.7 * np.log(t_soil) / Wr, 0.9) * P
        else:
            Ebl = 0
    return Ebl

#def RiceRootBiomass(W):
    CrtV = 1
    WTotal = W * 1000  # mg/m^2
    while CrtV > 0.0001:
        CrtV = 0.212 * (WTotal ** 0.936) + W * 1000 - WTotal
        WTotal += CrtV
    Wroot = (WTotal / 1000) - W
    return Wroot

def CH4RiceEf(CH4RiceEfC, W, Wmax):
    if Wmax == 0:
        return np.nan
    else:
        Fp = CH4RiceEfC * (1 - (W / Wmax)) ** 0.25
    return Fp


#####yuan 重新设计灌溉模式####################
def FillWaterPtn(PintWaterPtn, PintSDur, Sand, 
                  Cali_L=7, BasicFldDays=15, BasicMidDrnDays=3, 
                  BasicRefldDays=10, EndDrnDays=15):
    i_L = 0  # 初始化累计天数为0
    aryWater = {'Regime': [], 'days': []}

    if PintWaterPtn == 1: 
        aryWater['Regime'] = [1, 2, 1, 3, 2] # 1:淹水, 2:中期排水, 3:复淹
        aryWater['days'].append(min(PintSDur, BasicFldDays + Cali_L * round(PintSDur / 40)))
        i_L += aryWater['days'][0]
        aryWater['days'].append(min(max(0, PintSDur - i_L), BasicMidDrnDays + int((1 - Sand / 100) * 10)))
        i_L += aryWater['days'][1]
        aryWater['days'].append(min(max(0, PintSDur - i_L), BasicRefldDays + 3 * round(PintSDur / 40)))
        i_L += aryWater['days'][2]
        aryWater['days'].append(max(max(PintSDur - i_L, 0) - EndDrnDays, 0))
        i_L += aryWater['days'][3]
        aryWater['days'].append(max(0, PintSDur - i_L))

    elif PintWaterPtn == 2:
        aryWater['Regime'] = [1, 2, 3, 2] 
        aryWater['days'].append(min(PintSDur, BasicFldDays + Cali_L * round(PintSDur / 40)))
        i_L += aryWater['days'][0]
        aryWater['days'].append(min(max(0, PintSDur - i_L), BasicMidDrnDays + int((1 - Sand / 100) * 10)))
        i_L += aryWater['days'][1]
        aryWater['days'].append(max(max(PintSDur - i_L, 0) - EndDrnDays, 0))
        i_L += aryWater['days'][2]
        aryWater['days'].append(max(0, PintSDur - i_L))

    elif PintWaterPtn == 3:
        aryWater['Regime'] = [1, 3, 2]
        aryWater['days'].append(min(PintSDur, BasicFldDays + Cali_L * round(PintSDur / 40)))
        i_L += aryWater['days'][0]
        aryWater['days'].append(max(max(PintSDur - i_L, 0) - EndDrnDays, 0))
        i_L += aryWater['days'][1]
        aryWater['days'].append(max(0, PintSDur - i_L))

    elif PintWaterPtn == 4: 
        aryWater['Regime'] = [1, 2]
        aryWater['days'].append(max(0, PintSDur - EndDrnDays))
        i_L += aryWater['days'][0]
        aryWater['days'].append(max(0, PintSDur - i_L))

    elif PintWaterPtn == 5: 
        aryWater['Regime'] = [3, 2]
        aryWater['days'].append(max(0, PintSDur - EndDrnDays))
        i_L += aryWater['days'][0]
        aryWater['days'].append(max(0, PintSDur - i_L))

    return aryWater

def EhSmthDecrease(UseFormula, Eh, EhBase, EhStd, EhR):
    EhR1 = 0.16
    if UseFormula:
        if Eh < EhBase:
            Result = Eh - EhvalueD(Eh, EhBase + EhStd, 0.13, 1)
            if Result > EhBase:
                UseFormula = False
                Result = (EhBase - EhStd) + 2 * EhStd * np.random.uniform()
        else:
            Result = Eh - EhvalueD(Eh, EhBase - EhStd, EhR1, EhR)
            if Result < EhBase:
                UseFormula = False
                Result = (EhBase - EhStd) + 2 * EhStd * np.random.uniform()
    else:
        Result = (EhBase - EhStd) + 2 * EhStd * np.random.uniform()

    return Result

#def CH4Flux_day(day_begin, day_end, IP, sand, Tair, OMS, OMN, GY):
    GY *= 0.1
    OMN *= 0.1
    OMS *= 0.1
    StartDate = day_begin
    EndDate = day_end
    DurDate = EndDate - StartDate + 1
    result = pd.DataFrame({
        'DAT': np.zeros(DurDate), 
        'W': np.zeros(DurDate),
        'Wroot': np.zeros(DurDate),
        'OMN': np.zeros(DurDate),
        'OMS': np.zeros(DurDate),
        'Tsoil': np.zeros(DurDate),
        'Eh': np.zeros(DurDate),
        'Com': np.zeros(DurDate),
        'Cr': np.zeros(DurDate),
        'P': np.zeros(DurDate),
        'FEh': np.zeros(DurDate),
        'Ebl': np.zeros(DurDate),
        'Ep': np.zeros(DurDate),
        'E': np.zeros(DurDate)
    })

    RiceR = 0.1 - (DurDate / 70 - 1) * 0.03
    W0 = max(20 - (DurDate / 70 - 1) * 8, 1.0)  # 确保W0至少为1.0

    Flooded = True
    VI = 1
    w = 0
    SI = 0.325 + 0.0225 * sand
    Wmax = 9.46 * GY ** 0.76
    Eh = 250
    EhValueInit = 250
    aryWater = FillWaterPtn(IP, DurDate, sand)
    WRgm = aryWater['Regime'][w]
    WRgmDays = aryWater['days'][w]
    Q10 = 3
    Eh0 = 250
    WaterC = 0.636
    EhBase = -20

    for i in range(DurDate):
        result.loc[i, 'DAT'] = i + StartDate
        tmp = Tair[i]
        tsoil = 4.4 + 0.76 * tmp
        result.loc[i, 'Tsoil'] = tsoil

        TI = TemperatureIndex(Q10, tsoil)

        W = ShootBiomass(t=i + 1, r=RiceR, W0=W0, Wmax=Wmax)
        result.loc[i, 'W'] = W

        Cr = 0.0018 * VI * SI * W ** 1.25
        result.loc[i, 'Cr'] = Cr

        WI = 0.49 * np.exp(3.88 * WaterC - 5.4 * (WaterC ** 2))
        OMNC = WI * SI * TI * 0.027 * OMN
        OMSC = WI * SI * TI * 0.003 * OMS
        OMN -= OMNC
        OMS -= OMSC
        Com = OMNC + OMSC
        result.loc[i, 'OMN'] = OMN
        result.loc[i, 'OMS'] = OMS
        result.loc[i, 'Com'] = Com
        CI = 0

        if WRgm == 1:
            Eh -= EhvalueD(Eh, -1 * Eh0, 0.125 * (1 - W / Wmax) ** 4 + 0.04, OMNC)
            WaterC = 0.636
        elif WRgm == 2:
            Eh -= EhvalueD(Eh, EhValueInit, 0.098 * np.exp(-0.6 * CI), 1)
            WaterC -= EhvalueD(WaterC, 0.2, 0.1, 1)
        elif WRgm == 3:
            Eh = EhSmthDecrease(Flooded, Eh, EhBase, 20, 0.125 * (1 - W / Wmax) ** 4 + 0.04)
            WaterC = 0.45 + 0.13 - 0.13 * np.random.uniform()

        result.loc[i, 'Eh'] = Eh

        WRgmDays -= 1
        l = len(aryWater['Regime']) - 1
        if WRgmDays == 0 and w < l:
            w += 1
            WRgm = aryWater['Regime'][w]
            WRgmDays = aryWater['days'][w]

        f = FEh(Eh)
        CH4Production = max(0, 0.27 * f * (TI * Cr + Com))  # P
        result.loc[i, 'FEh'] = f
        result.loc[i, 'P'] = CH4Production

        Wr = RiceRootBiomass(W)
        result.loc[i, 'Wroot'] = Wr
        Ebl = CH4EmissionBbl(CH4Production, tsoil, Wr)  # Ebl
        result.loc[i, 'Ebl'] = Ebl

        if CH4Production > 0:
            CH4RiceEfC = min(0.55, 1 - Ebl / CH4Production)
        else:
            CH4RiceEfC = 0.55

        CH4RiceEF_L = CH4RiceEf(CH4RiceEfC, W, Wmax)  # Fp
        CH4RiceE = CH4Production * CH4RiceEF_L  # Ep
        CH4Emission = Ebl + CH4RiceE
        result.loc[i, 'Ep'] = CH4RiceE
        result.loc[i, 'E'] = CH4Emission  # g/m^2 * 10 -> kg/ha

    return result

def CH4Flux_coupled(day_begin, day_end, IP, sand, Tair, OMS, OMN, ATOPWTSeq, AROOTWTSeq):

    OMN *= 0.1
    OMS *= 0.1
    StartDate = day_begin
    EndDate = day_end
    DurDate = EndDate - StartDate + 1
    
    result = pd.DataFrame({
        'DAT': np.zeros(DurDate), 
        'W': np.zeros(DurDate),           # 地上部生物量 (来自Ricegrow)
        'Wroot': np.zeros(DurDate),       # 根系生物量 (来自Ricegrow)
        'OMN': np.zeros(DurDate),
        'OMS': np.zeros(DurDate),
        'Tsoil': np.zeros(DurDate),
        'Eh': np.zeros(DurDate),
        'Com': np.zeros(DurDate),
        'Cr': np.zeros(DurDate),
        'P': np.zeros(DurDate),
        'FEh': np.zeros(DurDate),
        'Ebl': np.zeros(DurDate),
        'Ep': np.zeros(DurDate),
        'E': np.zeros(DurDate)
    })

    Flooded = True
    VI = 1
    w = 0 
    SI = 0.325 + 0.0225 * sand
    Eh = 250 # 初始氧化还原电位
    EhValueInit = 250 # 初始氧化还原电位值
    aryWater = FillWaterPtn(IP, DurDate, sand)
    WRgm = aryWater['Regime'][w]
    WRgmDays = aryWater['days'][w]
    Q10 = 3 # Q10值
    Eh0 = 250 #
    WaterC = 0.636
    EhBase = -20

    for i in range(DurDate):
        result.loc[i, 'DAT'] = i + StartDate
        tmp = Tair[i]
        tsoil = 4.4 + 0.76 * tmp
        result.loc[i, 'Tsoil'] = tsoil

        TI = TemperatureIndex(Q10, tsoil)

        ricegrow_day = i 
        
        if ricegrow_day < len(ATOPWTSeq):
            W = ATOPWTSeq[ricegrow_day]  # 地上部生物量 (kg/ha)
            Wr = AROOTWTSeq[ricegrow_day]  # 根系生物量 (kg/ha)
        else:
            # 如果超出Ricegrow数据范围，使用最后一个值
            W = ATOPWTSeq[-1] if len(ATOPWTSeq) > 0 else 0
            Wr = AROOTWTSeq[-1] if len(AROOTWTSeq) > 0 else 0
            
        result.loc[i, 'W'] = W
        result.loc[i, 'Wroot'] = Wr
        

        # 根系分泌物计算 (基于真实根系生物量)
        Cr = 0.0018 * VI * SI * W ** 1.25
        result.loc[i, 'Cr'] = Cr

        # 有机质分解
        WI = 0.49 * np.exp(3.88 * WaterC - 5.4 * (WaterC ** 2))
        OMNC = WI * SI * TI * 0.027 * OMN
        OMSC = WI * SI * TI * 0.003 * OMS
        OMN -= OMNC
        OMS -= OMSC
        Com = OMNC + OMSC
        result.loc[i, 'OMN'] = OMN
        result.loc[i, 'OMS'] = OMS
        result.loc[i, 'Com'] = Com
        CI = 0

        # 氧化还原电位计算 (考虑真实生物量)
        Wmax = max(ATOPWTSeq) if len(ATOPWTSeq) > 0 else W  # 最大生物量
        
        if WRgm == 1:
            Eh -= EhvalueD(Eh, -1 * Eh0, 0.125 * (1 - W / Wmax) ** 4 + 0.04, OMNC)
            WaterC = 0.636
        elif WRgm == 2:
            Eh -= EhvalueD(Eh, EhValueInit, 0.098 * np.exp(-0.6 * CI), 1)
            WaterC -= EhvalueD(WaterC, 0.2, 0.1, 1)
        elif WRgm == 3:
            Eh = EhSmthDecrease(Flooded, Eh, EhBase, 20, 0.125 * (1 - W / Wmax) ** 4 + 0.04)
            WaterC = 0.45 + 0.13 - 0.13 * np.random.uniform()

        result.loc[i, 'Eh'] = Eh

        WRgmDays -= 1
        l = len(aryWater['Regime']) - 1
        if WRgmDays == 0 and w < l:
            w += 1
            WRgm = aryWater['Regime'][w]
            WRgmDays = aryWater['days'][w]

        # 甲烷产生
        f = FEh(Eh)
        CH4Production = max(0, 0.27 * f * (TI * Cr + Com))
        result.loc[i, 'FEh'] = f
        result.loc[i, 'P'] = CH4Production

        # 甲烷排放
        Ebl = CH4EmissionBbl(CH4Production, tsoil, Wr)
        result.loc[i, 'Ebl'] = Ebl

        if CH4Production > 0:
            CH4RiceEfC = min(0.55, 1 - Ebl / CH4Production)
        else:
            CH4RiceEfC = 0.55

        CH4RiceEF_L = CH4RiceEf(CH4RiceEfC, W, Wmax)
        CH4RiceE = CH4Production * CH4RiceEF_L
        CH4Emission = Ebl + CH4RiceE
        result.loc[i, 'Ep'] = CH4RiceE
        result.loc[i, 'E'] = CH4Emission

    return result
