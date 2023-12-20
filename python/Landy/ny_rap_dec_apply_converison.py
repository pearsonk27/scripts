import sys

x_coef = 1.0498268526763628
x_intercept = -13.504897595725652
y_coef = 1.0633649701809174
y_intercept = -60.21272858955581

x = int(sys.argv[1])
y = int(sys.argv[2])

converted_x = round(x_coef * x + x_intercept)
converted_y = round(y_coef * y + y_intercept)

print(f'mv_v("{converted_y}", fpdex);')
print(f'mv_h("{converted_x}", fpdex);')
