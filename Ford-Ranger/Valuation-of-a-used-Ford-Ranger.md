# Valuation of a used Ford Ranger



## The dataset

[ford-ranger-2019-2023.xlsx](.\ford-ranger-2019-2023.xlsx)



## Algorithm

Please perform a regression of "Price" as Y, while "Year" and "Mileage" as X1 and X2.



## The Python Code



Python Code:

```python
import pandas as pd
import statsmodels.api as sm

# Read the data
df = pd.read_csv("ford-ranger-2019-2023.xlsx - Sheet1.csv")

# Prepare the data
X = df[["Year", "Mileage"]]
y = df["Price"]

# Add a constant for the intercept
X = sm.add_constant(X)

# Fit the OLS model
model = sm.OLS(y, X).fit()

# Print the summary
print(model.summary())
```



Code output:

```
                            OLS Regression Results                            
==============================================================================
Dep. Variable:                  Price   R-squared:                       0.879
Model:                            OLS   Adj. R-squared:                  0.871
Method:                 Least Squares   F-statistic:                     108.9
Date:                Thu, 16 Jul 2026   Prob (F-statistic):           1.76e-14
Time:                        04:18:15   Log-Likelihood:                -294.62
No. Observations:                  33   AIC:                             595.2
Df Residuals:                      30   BIC:                             599.7
Df Model:                           2                                         
Covariance Type:            nonrobust                                         
==============================================================================
                 coef    std err          t      P>|t|      [0.025      0.975]
------------------------------------------------------------------------------
const      -3.308e+06   5.64e+05     -5.866      0.000   -4.46e+06   -2.16e+06
Year        1657.4751    278.930      5.942      0.000    1087.823    2227.127
Mileage       -0.0836      0.008    -10.512      0.000      -0.100      -0.067
==============================================================================
Omnibus:                        0.058   Durbin-Watson:                   2.031
Prob(Omnibus):                  0.971   Jarque-Bera (JB):                0.253
Skew:                           0.059   Prob(JB):                        0.881
Kurtosis:                       2.587   Cond. No.                     1.95e+08
==============================================================================

Notes:
[1] Standard Errors assume that the covariance matrix of the errors is correctly specified.
[2] The condition number is large, 1.95e+08. This might indicate that there are
strong multicollinearity or other numerical problems.
```



## The Summary

Here are the results of the multiple linear regression using **Price** as the dependent variable ($Y$) and **Year** ($X_1$) and **Mileage** ($X_2$) as the independent variables:

### Regression Equation

$$
\text{Price} = -3,308,000 + 1,657.48(\text{Year}) - 0.0836(\text{Mileage})
$$

### Key Findings & Interpretation

- **Year ($X_1$):** The coefficient for Year is **1,657.48**. This means that, assuming the mileage is kept constant, every newer model year adds approximately **$1,657.48** to the price of the Ford Ranger. This relationship is statistically significant ($p < 0.001$).
- **Mileage ($X_2$):** The coefficient for Mileage is **-0.0836**. This means that for every additional mile driven, the price decreases by roughly **8.4 cents** (or an $83.60 drop for every 1,000 miles), assuming the model year remains constant. This is also statistically significant ($p < 0.001$).
- **Model Fit (R-squared):** The R-squared value is **0.879**. This is a very strong fit, indicating that almost **88%** of the variation in the vehicle's price is explained by its age (Year) and wear (Mileage).
- **Intercept (Constant):** The intercept is heavily negative (-3.3 million), which represents the mathematical baseline if the Year and Mileage were both exactly zero. While crucial for the math to work, it has no real-world interpretation since there is no Year 0 Ford Ranger.

Overall, the regression confirms what we intuitively expect: newer cars command higher prices, and higher mileage significantly depreciates the value, with this specific model capturing those trends very accurately.



## Application

A 2019 Ford Ranger XLT Fx4 with 144,000 kilometers shall have a price of:
$$
Price = -3308000 + 1657.48*2019 - 0.0836*144000 = 26413.72
$$
The Dealer will sell it at $26,413 and a Private sales shall look at $23,413 if the car is clean.