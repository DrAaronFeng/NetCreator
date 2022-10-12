# NetCreator v1.3

Cinema 4D plugin for creating linking-splines effect which created by 3D artist Lewis Orton. For some reason the previous version (V1.0-V1.2) of NetCreator is no longer updated and maintained by Lewis, but Lewis decide to open source this plugin so that anyone who need it can modify by themselves. 

The previous version  (V1.0-V1.2) could not work normally with relatively new Cinema 4D released version. So I do some work to modify the code and update this plugin in order to compatible with the latest version Cinema 4D (R23...), NetCreator V1.3 released under GPL-3.0 License, thanks a lot to Lewis Orton for his excellent work!


Whats new in V1.3：

– Fixed runtime issue in Cinema 4D: there is an error infomation when parameter “Propagation” is checked:

AttributeError: type object 'c4d.plugins.NodeData' has no attribute 'GetDEnabling'Traceback (most recent call last).

– Fixed Issue where parameters “Strength” and “Size” could not coordinate unavailable as parameter “Turblence” is unchecked.

– Now NetCreator could perfectly compatibility with Cinema 4D R23.

– Improved: Increase parameter “Factor” in order to accurate adjustment the speed of Propagation for VertexMap if the propagation process is too fast.


How to install NetCreator：

You only need to download the NetCreator-1.3 and unzip it to your “Cinema 4D RXX/plugins” folder, it contains the source codes as well.


For more information please check:

V1.0-V1.2: https://www.behance.net/gallery/38292207/NetCreator-v11-Cinema-4D-plugin

V1.3:      http://www.wise4d.com/netcreator-v1-3-plugin-is-now-compatible-with-cinema-4d-r23/
