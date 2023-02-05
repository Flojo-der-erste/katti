import setuptools

setuptools.setup(
    name='katti',
    version='0.1',
     packages=setuptools.find_packages(),
package_data={'seleniumwire': ['ca.crt', 'ca.key']}

 )
