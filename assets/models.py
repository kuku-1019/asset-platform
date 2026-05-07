from django.db import models
from django.contrib.auth.models import User


class Department(models.Model):
    name = models.CharField(max_length=20, verbose_name='部门名称')
    # 这里的 'self' 是正确的，必须加引号
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children',
                               verbose_name='上级部门')

    class Meta:
        verbose_name = '部门'
        verbose_name_plural = '部门管理'

    # 建议加上这个，以后在后台显示部门名字，而不是 "Department object (1)"
    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=20, verbose_name='资产分类')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '分类'
        verbose_name_plural = '资产分类'


class Asset(models.Model):
    # 变量名建议大写，符合规范
    STATUS_CHOICES = (
        ('待入库', '待入库'),
        ('闲置中', '闲置中'),
        ('使用中', '使用中'),
        ('维修中', '维修中'),
        ('已报废', '已报废')
    )

    name = models.CharField(max_length=20, verbose_name='资产名称')
    sn = models.CharField(max_length=30, unique=True, verbose_name='资产编号')
    price = models.DecimalField(decimal_places=2, max_digits=10, verbose_name='资产价格')
    purchase_date = models.DateField(verbose_name='操作时间')  # 这里没加 null=True，说明录入时必须填日期，这是合理的

    # 注意这里 choices 引用了上面的大写变量
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='闲置中', verbose_name='资产状态')

    # 这里用 'Category' 字符串或者 Category 类都可以，因为上面已经定义了
    category = models.ForeignKey('Category', on_delete=models.CASCADE, verbose_name='资产分类')
    department = models.ForeignKey('Department', on_delete=models.CASCADE, verbose_name='所属部门')

    # 【重点修改】去掉引号，直接用 User 类
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='使用人')

    class Meta:
        verbose_name = "资产"
        verbose_name_plural = "资产管理"

    def __str__(self):
        return f"{self.name} ({self.sn})"
