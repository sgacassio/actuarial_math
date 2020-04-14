import numpy as np
import pandas as pd
import plotly.graph_objects as go
import copy
from controls import PRODUCTS

class InsuranceHandler():
    '''
        This class is responsible to calculated a range of variable related to insurance pricing,
        such as net level premium, reserves.
        Four different products area allowed each one with its variations:
            Pure Endowment: d
            Endowment:D
            Life Insurance: A
            Annuity: a

    '''
    def __init__(self, df):
        '''
            Class constructor:
                Input: pandas dataframe --> required
            All variables are populated according to the methods used.
            Example:
                When calc_premium is called all the variables required on premiums calculation are
                populated.
        '''
        #all life tables
        self.df = df
        #filtered life table which will be used on the calculations
        self.df_ = None
        #interest rate provided
        self.last_i_rate_used = None
        #max age of the table
        self.max_age = None
        #commutations
        self.Dx = None
        self.Cx = None
        self.Nx = None
        self.Mx = None
        #age
        self.age = None
        #net single premium
        self.pup = None
        #self.anui is "a" in the formula Pa = A, where P is net level premium
        self.anui = None
        #net level premium
        self.pna = None
        #benefit differed period
        self.dif_benef = None
        #benefit term
        self.term_benef = None
        #antecipated indicator
        self.antecip_benef = None
        #product
        self.prod = None
        #payment diferred period
        self.dif_pay = None
        #payment term
        self.term_pay = None
        #antecipated indicator for payment
        self.antecip_pay = None

        #commutation used on reserves calculation
        self.Dx__ = None
        self.Cx__ = None
        self.Nx__ = None
        self.Mx__ = None

        #reserves
        self.last_prosp_reserve = None
        self.last_retro_reserve = None

        #paid up
        self.paidup = None
        #extended
        self.extended = None

    def __pv_calc__(self, n, i=0):
        '''
            This method calculates the present value factor v
            Input:
                n: period --> int or np.array
                i: interest rate --> float
            Output:
                A float or a vector of floats with the factor (1+rate)**(-n)
        '''
        rate = i if i>0 else self.last_i_rate_used
        return 1/(1 + rate)**n

    def __calc_Dx__(self, i=0):
        '''
            This method calculates the Dx commutation
            Input:
                i: interest rate, default = 0 --> float
            Output:
                  An np.array with Dx commutation
        '''
        lx = self.df_['lx'].values
        age = self.df_['age'].values

        return lx*self.__pv_calc__(age, i)

    def __calc_Nx__(self, option='normal'):
        '''
            Thist method calculates the Nx commutation
            Input:
                option: normal or reserves, default = normal --> str
            Output:
                  An np.array with Nx commutation
        '''
        if option=='normal':
            return self.Dx[::-1].cumsum()[::-1]
        else:
            return self.Dx__[::-1].cumsum()[::-1]

    def __calc_Cx__(self, i=0):
        '''
            This method calculates the Cx commutation
            Input:
                i: interest rate, default = 0 --> float
            Output:
                  An np.array with Cx commutation
        '''
        dx = self.df_['dx'].values
        age = self.df_['age'].values
        age_ = age + 1

        return dx*self.__pv_calc__(age_,i)

    def __calc_Mx__(self, option='normal'):
        '''
            This method calculates the Nx commutation
            Input:
                option: normal or reserves, default = normal --> str
            Output:
                  An np.array with Mx commutation
        '''
        if option=='normal':
            return self.Cx[::-1].cumsum()[::-1]
        else:
            return self.Cx__[::-1].cumsum()[::-1]

    def __verify_prod__(self, x, n, m, antecip, prod):
        '''
            This method verify whetheer the combination of age, differed period and term make is aceptable
            or not, based on the life table length
            Input:
                x: age
                b: deffered period
                m: term
                antecip: indicates whether the product is antecipated or not
            Output:
                raise and exception if the combination is not valid
        '''
        max_age = self.max_age

        add_one = 1 if antecip and prod == 'a' else 0

        m_ = 0 if m == np.inf else m

        criteria = x + n + m_ - add_one

        #pure endowment with diferred period
        if prod == 'd' and n > 0:
            raise Exception('Não existe dotal puro diferido')

        #whole life endowment
        if (prod == 'd' or prod == 'D') and m == np.inf:
            raise Exception('Não existe dotal vitalício')

        #combination of periods not supported by the table
        if criteria > max_age:
            raise Exception('Idade + diferimento + parazo = {} > {} idade máxima'.format(criteria, max_age))

    def __calc_pup__(self, dif, age, term=np.inf, antecip=True, prod='a', option = 'normal'):

        if option == 'normal':
            Dx = self.Dx
            Cx = self.Cx
            Nx = self.Nx
            Mx = self.Mx
        else:
            Dx = self.Dx__
            Cx = self.Cx__
            Nx = self.Nx__
            Mx = self.Mx__

        max_age = self.max_age

        x = age
        n = dif
        m = term

        add_one = 0 if antecip and prod == 'a' else 1
        #remove_term used to settle whole life and m years products in the same formula
        remove_term = 0 if term == np.inf else 1
        m_ = max_age - x - n - add_one if m == np.inf else m

        self.__verify_prod__(x, n, m, antecip, prod)
        #Endowment net single premium
        if prod == "D":
            pup = (Mx[x + n] - Mx[x + n + m_] + Dx[x + n + m_]) / \
                    Dx[x]
        #Pure Endowment net single premium
        elif prod == "d":
            pup = Dx[x + m_] / Dx[x]
        #Life insurance net single premium
        elif prod == "A":
            pup = (Mx[x + n] - remove_term*Mx[x + n + m_]) / \
                    Dx[x]
        #Annuity net single premium
        elif prod == "a":
            pup = (Nx[x + n + add_one] - remove_term*Nx[x + n + m_ + add_one]) / \
                     Dx[x]
        return pup

    def __calc_prov_retro__(self, t):
        '''
            This method calculates reserves using the retrospective method
            Input:
                t: evaluation time
            Output:

        '''
        max_x = self.max_age
        x = self.age
        n = self.dif_benef
        m = self.term_benef
        i = self.dif_pay
        k = self.term_pay
        prod = self.prod
        pay_antecip = self.antecip_pay
        benef_antecip = self.antecip_benef

        adjust_pay = 1 if pay_antecip else 0
        adjust_benef = 1 if benef_antecip and prod == 'a' else 0

        P = self.pna
        #present value factor
        E = 1/self.__calc_pup__(0, x, t, pay_antecip, 'd', 'reserves')
        #payment
        if  0 < t <= i - adjust_pay:
            a = 0
        elif i - adjust_pay < t:
            #The net single premium function is used varying only the parameter according to
            #the position of "t"
            #The option "reserves" is given to allow simulations with different values of interest rate
            a = self.__calc_pup__(i, x, min(t-i, k), pay_antecip, 'a', 'reserves')


        #benefit
        if 0 < t <= n - adjust_benef:
            A = 0
        elif n - adjust_benef < t:
            #adjustment for endowments
            #For restrospective method the endowment must be seen as a life insurance while t is
            #smaller than m + n
            if prod == "D" and t<=m+n:
                A = self.__calc_pup__(n, x, min(t-n,m), benef_antecip, "A", 'reserves')
            elif prod == 'd' and t <= m:
                #for t <= m you only can "see" the payments
                A = 0
            else:
                #general case
                A = self.__calc_pup__(n, x, min(t-n,m), benef_antecip, prod, 'reserves')

        #Adjustment for points with zero reserves
        if t == 0:
            A = 0
            a = 0

        if t < n and t < i:
            A = 0
            a = 0

        if t > m+n and t > k+i:
            a = 0
            A = 0

        V = (P*a - A)*E
        return V

    def __calc_paidup__(self, A, V, i, k, t, n, m, prod, benef_antecip):
        '''
            This method calculates a paidup insurance, annuity or endowment
            Input:
                A: product net single premium until t
                V: reserve until t
            Output:

        '''
        if i < t < k:
            self.paidup = V/A
        else:
            self.paidup = 0


        if  i < t < k:
            if prod == 'A' or prod == 'a':
                #search for the m which minimize the distance between V and the new A
                #As the time unit measure is year the difference between V and A will be > 0
                values_ = list()
                for period in range(1, min(m, self.max_age-t)):
                    try:
                        prod_values = self.__calc_pup__(min(n-t,0), self.age+t, term=period,
                                                    antecip=benef_antecip,
                                                    prod=prod, option = 'normal')
                        values_.append(abs(V - prod_values))
                    except:
                        pass

                if values_:
                    self.extended = [np.array([values_]).argmin() + 1]
                else:
                    self.extended = [0]

            elif prod == 'D':
                insurance = 0
                try:
                    if t <= n:
                        insurance = self.__calc_pup__(max(n-t,0), self.age+t, term=m,
                                              antecip=benef_antecip,
                                              prod='A', option = 'normal')
                    else:
                        insurance = self.__calc_pup__(0, self.age+t, term=m-t,
                                              antecip=benef_antecip,
                                              prod='A', option = 'normal')

                except:
                    pass

                if V >= insurance:
                    d = 1
                    try:
                        d = self.__calc_pup__(0, self.age+t, term=m+n-t,
                                          antecip=benef_antecip,
                                          prod='d', option = 'normal')
                    except:
                        pass

                    endowment = (V - insurance) / d
                    self.extended = [m, endowment]
                else:
                    values_ = list()
                    for period in range(1, min(m, self.max_age-t)):
                        try:
                            prod_values = self.__calc_pup__(min(n-t,0), self.age+t, term=period,
                                                        antecip=benef_antecip,
                                                        prod='A', option = 'normal')
                            values_.append(abs(V - prod_values))
                        except:
                            pass
                    if values_:
                        self.extended = [np.array([values_]).argmin() + 1]
                    else:
                        self.extended = [0]
            elif prod == 'd':
                self.extended = [0]
        else:
            self.extended = [0]

    def __calc_prov_prosp__(self, t):
        '''
            This method calculates reserves using the prospective method
            Input:
                t: evaluation time
            Output:

        '''

        max_x = self.max_age
        x = self.age
        n = self.dif_benef
        m = self.term_benef
        i = self.dif_pay
        k = self.term_pay
        prod = self.prod
        pay_antecip = self.antecip_pay
        benef_antecip = self.antecip_benef

        adjust_pay = 1 if pay_antecip else 0
        adjust_benef = 1 if benef_antecip and prod == 'a' else 0

        P = self.pna

        #payment

        #The net single premium function is used varying only the parameter according to
        #the position of "t"
        #The option "reserves" is given to allow simulations with different values of interest rate
        if 0 < t <= i - adjust_pay:
            a = self.__calc_pup__(max(i-t, 0), x+t, k, pay_antecip, 'a', 'reserves')
        elif i - adjust_pay < t:
            a = self.__calc_pup__(0, x+t, max(i+k-t,0), pay_antecip, 'a', 'reserves')

        #benefit
        #The net single premium function is used varying only the parameter according to
        #the position of "t"
        #The option "reserves" is given to allow simulations with different values of interest rate
        if 0 < t <= n - adjust_benef:
            A = self.__calc_pup__(max(n-t,0), x+t, m, benef_antecip, prod, 'reserves')
        elif n - adjust_benef < t <= n + m - adjust_benef:
            A = self.__calc_pup__(0, x+t, max(n + m - t,0), benef_antecip, prod, 'reserves')
        elif t > n + m - adjust_benef:
            A = 0


        #Adjustment for points with zero reserves
        if t == 0:
            A = 0
            a = 0

        if t < n and t < i:
            A = 0
            a = 0

        if t > m+n and t > k+i:
            a = 0
            A = 0

        self.__calc_paidup__(A, A - P*a, i, k, t, n, m, prod, benef_antecip)
        V = A - P*a
        return V

    def select_table(self, table, gender):
        '''
            This method selects a life table based on gender and life table name
            Input:
                table: life table name --> str
                gender: gender --> str
            Output:

        '''
        query_string = 'table == "{}" and gender == "{}"'.\
                                          format(table, gender)
        self.df_ = self.df.query(query_string).\
                                          reset_index(drop=True).copy()
        self.max_age = self.df_['age'].max()

    def gen_commutations(self, i_rate):
        '''
            This method calculates all the commutation functions based on a given interest rate
            Input:
                i_rate: interest rate --> float
            Ouput:

        '''
        if self.df_ is None:
            raise Exception('Life table must be filtered')

        self.last_i_rate_used = i_rate

        self.Dx = self.__calc_Dx__()
        self.Nx = self.__calc_Nx__()
        self.Cx = self.__calc_Cx__()
        self.Mx = self.__calc_Mx__()

    def calc_premium(self, age, dif_benef=0, term_benef=np.inf,
                     antecip_benef=True, prod='a',
                     dif_pay=0, term_pay=np.inf, antecip_pay=True):

        '''
            This method calculates the net single premium and net level premium
            Input:
                age: age --> int
                dif_benef: diferred period, default=0 --> int
                term_benef: benefit term, default=np.inf --> int
                antecip_benef: indicates whether the benefit is atecipated or not, default=True --> boolean
                prod: product (D:Endowment,d:pure endowment,A: life insurance,a:annuity), default=a --> str
                dif_pay: payment diferred period, default=0 --> int
                term_pay: payment term, default=np.inf --> int
                antecip_pay: indicates whether the paymeent is atecipated or not, default=True --> boolean
            Ouput:
        '''
        self.age = age

        self.pup = self.__calc_pup__(dif_benef, age, term_benef,
                                     antecip_benef, prod)
        self.dif_benef = dif_benef
        self.term_benef = term_benef
        self.antecip_benef = antecip_benef
        self.prod = prod

        self.anui = self.__calc_pup__(dif_pay, age, term_pay, antecip_pay, "a")
        self.dif_pay = dif_pay
        self.term_pay = term_pay
        self.antecip_pay = antecip_pay

        self.pna = self.pup / self.anui

    def calc_reserves(self, t, kind="prosp", rate=0):
        '''
            This method calculates reserves using the prospective and retrospective method
            Input:
                t: evaluation time
                kind: method (prosp or retrosp), default=prosp --> str
                rate: interest rate. Used to simulate interest rate variations, if not provided will use
                      the interest rate used to calculate the nsp and nlp
            Output:
                Reserve at time t --> float
        '''
        self.Dx__ = self.__calc_Dx__(rate)
        self.Nx__ = self.__calc_Nx__('reserves')
        self.Cx__ = self.__calc_Cx__(rate)
        self.Mx__ = self.__calc_Mx__('reserves')

        if kind == 'prosp':
            result = self.__calc_prov_prosp__(t)
            self.last_prosp_reserve = result
        elif kind == 'retrosp':
            result = self.__calc_prov_retro__(t)
            self.last_retro_reserve = result

        return result

def real_br_money_mask(my_value):
    a = '{:,.2f}'.format(float(my_value))
    b = a.replace(',','v')
    c = b.replace('.',',')
    return 'R$ ' + c.replace('v','.')


def generate_main_plot(handler_copy, dif_benef,
                       term_benef, product,
                       antecip_benef, value_bnf,
                       dif_pay=0, term_pay=np.inf,
                       antecip_pay=True):

    handler_copy_ = copy.copy(handler_copy)
    values = []
    for i_rate in [0.020, 0.025, 0.030,
                   0.035, 0.040, 0.045, 0.050,
                   0.055, 0.060, 0.065, 0.070,
                   0.075, 0.080, 0.085, 0.090,
                   0.095, 0.100]:

        handler_copy_.gen_commutations(i_rate)
        for age in range(0, 81):
            cell = []
            try:
                handler_copy_.calc_premium(age=age,
                                           dif_benef=dif_benef,
                                           term_benef=term_benef,
                                           antecip_benef=antecip_benef,
                                           prod=product,
                                           dif_pay=dif_pay,
                                           term_pay=term_pay,
                                           antecip_pay=antecip_pay)

                cell = [age, i_rate*100, handler_copy_.pna*value_bnf]
                values.append(cell)
            except:
                pass

    df_3d = pd.DataFrame(np.array(values))
    df_matrix = pd.crosstab(index=df_3d[0], columns= df_3d[1],
                                values=df_3d[2], aggfunc=np.sum)

    fig = go.Figure(data=[go.Surface(z=df_matrix,
                                 y=np.array(list(df_matrix.index)),
                                 x=np.array(list(df_matrix.columns)))])


    fig.update_layout(title=PRODUCTS[product], margin=dict(l=65, r=50, b=65, t=90),
                      scene = dict(
                      xaxis_title='Taxa de Juros a.a',
                      yaxis_title='Idade',
                      zaxis_title='PNA'),)

    return fig

def generate_reserves_plot(handler_copy, value_bnf):

    handler_copy_ = copy.copy(handler_copy)
    retro = []
    prosp = []
    t_ = []

    for t in range(0,100):
        try:
            retro.append(handler_copy_.calc_reserves(t, kind='retrosp')*value_bnf)
            prosp.append(handler_copy_.calc_reserves(t)*value_bnf)
            t_.append(t)
        except:
            pass

    l1 = len(t_)
    l2 = len(retro)
    l3 = len(prosp)
    t_ = t_[:min(l1,l2,l3)]
    retro = retro[:min(l1,l2,l3)]
    prosp = prosp[:min(l1,l2,l3)]

    reserves_df = pd.DataFrame().from_dict({'t':t_,
                                            'Retrospectiva':retro,
                                            'Prospectiva':prosp})

    layout = go.Layout(title= "Reservas",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
            )
    fig = go.Figure(layout=layout)

    fig.add_trace(go.Scatter(x=reserves_df['t'].values,
                             y=reserves_df['Retrospectiva'].values,
                             mode='lines',
                            name='Retrospectivo'))

    fig.add_trace(go.Scatter(x=reserves_df['t'].values,
                    y=reserves_df['Prospectiva'].values,
                    mode='lines+markers',
                    name='Prospectivo'))

    return fig

def generate_tables_plot(handler_copy,
                         gender, age,
                         i_rate, dif_bnf,
                         term_bnf,
                         antecip_bnf,
                         prod,
                         dif_pay,
                         term_pay,
                         antecip_pay,
                         value_bnf):

    handler_copy_ = copy.copy(handler_copy)
    tables = ['IBGE 2009', 'BR-EMSsb-v.2015',
              'BR-EMSmt-v.2015', ' AT2000', 'AT-49']
    pna_ =[]
    tbs_ = []
    for tb in tables:
        try:
            handler_copy_.select_table(tb, gender)
            handler_copy_.gen_commutations(i_rate)
            handler_copy_.calc_premium(age=age,
                                       dif_benef=dif_bnf,
                                       term_benef=term_bnf,
                                       antecip_benef=antecip_bnf,
                                       prod=prod,
                                       dif_pay=dif_pay,
                                       term_pay=term_pay,
                                       antecip_pay=antecip_pay)
            pna_.append(handler_copy_.pna*value_bnf)
            tbs_.append(tb)
        except:
            pass

    layout = go.Layout(title= "Comparação de Tábuas",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
            )

    fig = go.Figure([go.Bar(x=tbs_, y=pna_)], layout=layout)

    return fig
