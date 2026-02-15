print("Hello! This is a oneshot package example for PaxD. It demonstrates how to create a package that runs a single script and then uninstalls itself automatically after execution.")
link = input("This is also an example of a linker. This package can create a link for you to try! What should the link be called? ")
link_loc = input("Where should the link lead to? (dir) ")

import paxd_sdk # type: ignore
paxd_sdk.Links.NewLink(link, link_loc)

print("Should be done... If you want to, delete this link at your PaxDs links directory. (`paxd packagedir` > com.mralfiem591.paxd > links, delete that folder)")