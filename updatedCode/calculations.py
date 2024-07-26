# main file is main.py

# imports
from scipy.stats.mstats import hmean
import itertools
import pandas as pd


def define_MapNo(df_art_si_tmc2):
    df_art_mapno = df_art_si_tmc2[df_art_si_tmc2['congestion_level'].isin(["Moderate",'Heavy','Severe'])].\
                   sort_values(['peak','tmc','link']).reset_index().drop(columns = {"index"})

    if df_art_mapno.shape[0] > 0:
        tmc_list_arterial = df_art_mapno.reset_index().groupby(['peak','tmc']).agg({"index":"first"}).reset_index()['index'].tolist() + [df_art_mapno.reset_index().groupby(['peak','tmc']).agg({"index":"last"}).reset_index()['index'].tolist()[-1:][0] + 1]
        corder_list_arterial = df_art_mapno['link'].tolist()
        g = 0
        g_list_arterial = []
        for i in range(len(tmc_list_arterial) - 1):
            pos = tmc_list_arterial[i]
            pos_next = tmc_list_arterial[i + 1]
            g1_value = corder_list_arterial[pos: pos_next]
            g = g + 1
            cur_g_list= [g]
            for j in range(len(g1_value) - 1):
                cur_g1_value = g1_value[j]
                next_g1_value = g1_value[j+1]
                if next_g1_value - cur_g1_value <= 3:
                    g = g
                    cur_g_list.append(g)
                else:
                    g = g + 1
                    cur_g_list.append(g)
            g_list_arterial.append(cur_g_list)
        mapno_arterial = list(itertools.chain.from_iterable(g_list_arterial))
        pd_arterial_si_tmc = df_art_mapno
        pd_arterial_si_tmc['MapNo'] = mapno_arterial

        return pd_arterial_si_tmc

def calc_pti_tti(art_map,df):
    df_ = df.drop_duplicates(subset=['tmc','link'])
    df_art_map = art_map[["MapNo",'peak','tmc','link']].\
        merge(df_, on = ['tmc','link'], how = 'left').sort_values(['MapNo','peak','tmc'])


    df_art_am_pti = df_art_map.groupby(['MapNo','tmc','link','month','dow','hour','peak']).\
                    agg({"speed":[hmean,q95,"mean"],"historical_average_speed":[hmean,"first"],
                         "miles":"first"}).reset_index()

    df_art_am_pti.columns = ['MapNo','tmc','link','month','dow','hour','peak','hmean_speed_capped','95_speed_capped',
                                'avg_speed_capped','hmean_free_flow_speed','free_flow_speed','length']



    df_art_am_pti['ratio1_h'] = df_art_am_pti['hmean_free_flow_speed']/df_art_am_pti['hmean_speed_capped']
    df_art_am_pti['ratio2'] = df_art_am_pti['free_flow_speed']/df_art_am_pti['avg_speed_capped']

    df_art_am_pti_grp = df_art_am_pti.groupby(['MapNo','peak']).\
                    agg({"hmean_speed_capped":["sum","mean"],"hmean_free_flow_speed":["sum","mean"],
                        "free_flow_speed":"sum","avg_speed_capped":"sum","ratio1_h":q95,"ratio2":q95}).reset_index()
    df_art_am_pti_grp.columns = ['MapNo','peak','hmean_speed_capped_sum','hmean_speed_capped_avg','hmean_free_flow_speed_sum',
                            'hmean_free_flow_speed_avg','free_flow_speed_sum','avg_speed_capped_sum','PTI_hmean',
                            'PTI_mean']




    df_art_am_pti_grp['TTI_hmean'] = df_art_am_pti_grp['hmean_free_flow_speed_sum']/df_art_am_pti_grp['hmean_speed_capped_sum']
    df_art_am_pti_grp['TTI_mean'] = df_art_am_pti_grp['free_flow_speed_sum']/df_art_am_pti_grp['avg_speed_capped_sum']
    df_art_am_pti_grp = df_art_am_pti_grp[["MapNo","PTI_hmean","PTI_mean","TTI_hmean","TTI_mean","peak"]].sort_values('MapNo')

    return df_art_am_pti_grp

def q85(x):
    return x.quantile(0.85)
def q95(x):
    return x.quantile(0.95)
def Calculate_Speed_Index(df, rd_type, period):
    df_filt = df[(df['road_type'] == rd_type) & (df['period'] == period)]
    if df_filt.shape[0]>0:
        df_filt = df_filt.groupby(['tmc','link','hour']).agg({'speed':hmean}).reset_index().\
                    rename(columns = {"speed":"hmean_speed_capped"}).merge(df_filt.groupby(['tmc','link']).\
                    agg({"speed":q85, "historical_average_speed":"mean"}).\
                    rename(columns = {"speed":"ff_speed_capped_tmc","historical_average_speed":"avg_free_flow_speed"}).\
                    reset_index(),on = ['tmc','link'],how = 'left')

        df_filt['speed_index1'] = df_filt['hmean_speed_capped']/df_filt['ff_speed_capped_tmc']
        df_filt['speed_index2'] = df_filt['hmean_speed_capped']/df_filt['avg_free_flow_speed']
        df_filt = df_filt.sort_values(['tmc','link','hour'])
        df_SI = df_filt.pivot_table(index=['tmc','link'], columns='hour',
                            values=['speed_index1','speed_index2']).reset_index()

        if period == 'AM':
            df_SI.columns = ['tmc', 'link', 'SI1_6AM', 'SI1_7AM', 'SI1_8AM','SI2_6AM', 'SI2_7AM', 'SI2_8AM']
            df_SI["SI1"] = (df_SI['SI1_6AM'] + df_SI['SI2_6AM'])/2
            df_SI["SI2"] = (df_SI['SI1_7AM'] + df_SI['SI2_7AM'])/2
            df_SI["SI3"] = (df_SI['SI1_8AM'] + df_SI['SI2_8AM'])/2
            df_SI["SI"] = (df_SI['SI1'] + df_SI['SI2'] + df_SI['SI3'])/3
            df_SI = df_SI[['tmc' , 'link', 'SI1',    'SI2',    'SI3',  'SI']]
        else:
            df_SI.columns = ['tmc', 'link', 'SI1_15PM', 'SI1_16PM', 'SI1_17PM','SI2_15PM', 'SI2_16PM', 'SI2_17PM']
            df_SI["SI1"] = (df_SI['SI1_15PM'] + df_SI['SI2_15PM'])/2
            df_SI["SI2"] = (df_SI['SI1_16PM'] + df_SI['SI2_16PM'])/2
            df_SI["SI3"] = (df_SI['SI1_17PM'] + df_SI['SI2_17PM'])/2
            df_SI["SI"] = (df_SI['SI1'] + df_SI['SI2'] + df_SI['SI3'])/3
            df_SI = df_SI[['tmc' , 'link', 'SI1',    'SI2',    'SI3',  'SI']]

        df_SI['peak'] = period
    else:
       df_SI = pd.DataFrame(columns =['tmc' , 'link', 'SI1',    'SI2',    'SI3',  'SI','peak'] )

    return df_SI


def combine_SI_AM_PM(df_art_am, df_art_pm, df_static, road_type):
# def combine_SI_AM_PM(df_art_am, df_art_pm, road_type):
    if road_type == "arterial":
        # the1 = 0.44; the2 = 0.53; the3 = 0.74
        the1 = 0.64; the2 = 0.73; the3 = 0.88
    else:
        # the1 = 0.6; the2 = 0.8; the3 = 0.9
        the1 = 0.7; the2 = 0.9; the3 = 0.95


    df_art_am_pm = pd.concat([df_art_am,df_art_pm],axis=0)
    df_art_am_pm["congestion_level"] = "Light"

    df_art_am_pm["congestion_level"] = df_art_am_pm["SI"].apply(lambda x:
    'Severe' if x <=the1 else
    ('Heavy' if x>the1 and x<=the2 else
    ('Moderate' if x>the2 and x<=the3 else 'Light')))

    df_art_si_tmc = df_art_am_pm.merge(df_static, on = ['tmc','link'], how = "left")
    df_art_si_tmc = df_art_si_tmc.sort_values(['peak','tmc','link'])

    return df_art_si_tmc


# def prep_data(result_df): #!!!!!
#     result_df['measurement_tstamp'] = pd.to_datetime(result_df['measurement_tstamp'])
#     result_df['hour'] = result_df['measurement_tstamp'].dt.hour
#     result_df['dow'] = result_df['measurement_tstamp'].dt.weekday
#     result_df['month'] = result_df['measurement_tstamp'].dt.month
#     result_df = result_df[result_df['hour'].isin([6,7,8,15,16,17])]
#     result_df.rename(columns={'tmc_code':'tmc'}, inplace=True)


#     # result_df = result_df[['tmc', 'road', 'direction', 'county', 'miles', 'road_order', 'f_system']]
#     result_df.rename(columns={'road_order':'link'}, inplace=True)
#     result_df['f_system'] = result_df['f_system'].astype(int)
#     result_df['road_type'] = result_df['f_system'].apply(lambda x: 'freeway' if x in [1,2] else 'arterial')

#     result_df['period']= result_df['hour'].apply(lambda x: 'AM' if x in [6,7,8] else 'PM')
#     return result_df


def prep_data(result_df):

    result_df['hh'] = result_df['hh'].astype(int)
    result_df['avg_speed'] = result_df['avg_speed'].astype(float)
    result_df['ffs'] = result_df['ffs'].astype(float)
    result_df['link'] = result_df['link'].astype(int)
    result_df['dt'] = pd.to_datetime(result_df['dt'])
    result_df['month'] = result_df['dt'].dt.month
    result_df['dow'] = result_df['dt'].dt.weekday
    result_df['year'] = result_df['dt'].dt.year
    result_df = result_df[result_df['hh'].isin([6,7,8,15,16,17])]
    result_df['period']= result_df['hh'].apply(lambda x: 'AM' if x in [6,7,8] else 'PM')
    result_df['road_type']='arterial'
    result_df.rename(columns={"hh": "hour", "avg_speed": "speed","ffs": "historical_average_speed" ,"length":"miles"}, inplace= True)

    return result_df


def calculate_arterial(result_df):
    df_art_pm = Calculate_Speed_Index(result_df, 'arterial','PM')
    df_art_am = Calculate_Speed_Index(result_df, 'arterial','AM')
    df_art_out = combine_SI_AM_PM(df_art_am, df_art_pm, result_df,'arterial')
    art_map = define_MapNo(df_art_out)
    art_pti_tti = calc_pti_tti(art_map,result_df)
    art_pti_tti = art_map.merge(art_pti_tti, on = ['MapNo','peak'], how = 'left')
    arterials_out_ = art_pti_tti.merge(df_art_out, on = df_art_out.columns.values.tolist(), how = 'right').sort_values(['peak','MapNo']).\
                    reset_index().drop(columns = {"index"})
    # arterials_out_ = arterials_out_.groupby(['tmc', 'peak']).first().reset_index()!!
    # arterials_out_ = arterials_out_.drop(columns=['measurement_tstamp', 'speed'])!!
    # arterials_out_.to_csv('arterials.csv', index=True)
    return arterials_out_

def calculate_freeway(result_df):
    df_free_am = Calculate_Speed_Index(result_df, 'freeway','AM')
    df_free_pm = Calculate_Speed_Index(result_df, 'freeway','PM')
    df_free_out = combine_SI_AM_PM(df_free_am, df_free_pm, result_df,'freeway')
    free_map = define_MapNo(df_free_out)
    free_pti_tti = calc_pti_tti(free_map,result_df)
    free_pti_tti = free_map.merge(free_pti_tti, on = ['MapNo','peak'], how = 'left')
    freeways_out_ = free_pti_tti.merge(df_free_out, on = df_free_out.columns.values.tolist(), how = 'right').sort_values(['peak','MapNo']).\
                    reset_index().drop(columns = {"index"})
    # freeways_out_ = freeways_out_.groupby(['tmc', 'peak']).first().reset_index()!!
    # freeways_out_ = freeways_out_.drop(columns=['measurement_tstamp', 'speed'])!!
    # freeways_out_.to_csv('freeways.csv', index=True)
    return freeways_out_

def arterial_spped_index(result_df_edit):
        arterials_am = Calculate_Speed_Index(result_df_edit, 'arterial', 'AM')
        arterials_pm = Calculate_Speed_Index(result_df_edit, 'arterial', 'PM')
        combined_arterials = combine_SI_AM_PM(arterials_am, arterials_pm, result_df_edit, 'arterial')
        return combined_arterials


