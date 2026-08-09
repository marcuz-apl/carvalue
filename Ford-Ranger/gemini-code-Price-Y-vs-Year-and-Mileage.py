import pandas as pd
import statsmodels.api as sm

# Read the data
df = pd.read_csv('ford-ranger-2019-2023.xlsx - Sheet1.csv')

# Prepare the data
X = df[['Year', 'Mileage']]
y = df['Price']

# Add a constant for the intercept
X = sm.add_constant(X)

# Fit the OLS model
model = sm.OLS(y, X).fit()

# Print the summary
print(model.summary())