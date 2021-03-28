Machine Notes: US Cutter Titan 3
--------------------------------

[Retailer Website](https://uscutter.com/TITAN-3-Vinyl-Cutter-ARMS-28-53-68-inch/)

This is probably the same as or similar to cutters sold by
[SAGA](https://vinyl-cutter.us/vinyl-cutters).


Connection Notes:
-----------------

Linux recognizes this plotter via the `usblp` module. HPGL plotting
code may be sent directly to plotter by writing to the device file. I
have not tested plotting from any graphics apps.

`dmesg` output on USB connect:
```
[2196315.586881] usb 3-6: new full-speed USB device number 16 using xhci_hcd
[2196315.760893] usb 3-6: New USB device found, idVendor=0483, idProduct=5750, bcdDevice= 2.00
[2196315.760896] usb 3-6: New USB device strings: Mfr=1, Product=2, SerialNumber=3
[2196315.760897] usb 3-6: Product: SAGA Cutter Plotter
[2196315.760898] usb 3-6: Manufacturer: SAGACNC
[2196315.760899] usb 3-6: SerialNumber: SAGA4iB5
[2196315.766935] usblp 3-6:1.0: usblp6: USB Bidirectional printer dev 16 if 0 alt 0 proto 2 vid 0x0483 pid 0x5750
```

Serial connection via FTDI serial adapter did not work. A null-modem
adapter may be necessary. As the USB connection works natively, I did
not investigate further.


Usage Notes:
------------

While highly functional and relatively easy to operate, this plotter
seems to support only a relatively limited subset of HPGL commands. In
particular, the `IP` and `SC` commands seem to have no effect. This
means that common HPGL idioms based on manipulation of origin and
scaling simply do not work, and geometric transforms must be carried
out on the vertex data itself prior to plotting. While I haven't
tested it, I would suspect that arc/curve commands are also
unsupported, as are labeling commands.

On the positive side, the plotter simply ignores unsupported commands
without interrupting the program. As a result, in-band markup of a
plotter program (such as using different `SP` pens to denote different
semantic categories) can be passed through to the plotter unchanged.