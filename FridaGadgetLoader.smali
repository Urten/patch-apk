.class public Lpatchapk/FridaGadgetLoader;
.super Landroid/app/Application;
.source "FridaGadgetLoader.java"


# direct methods
.method static constructor <clinit>()V
    .registers 1

    .line 7
    const-string v0, "frida-gadget"

    invoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V

    .line 8
    return-void
.end method

.method public constructor <init>()V
    .registers 1

    .line 5
    invoke-direct {p0}, Landroid/app/Application;-><init>()V

    return-void
.end method
