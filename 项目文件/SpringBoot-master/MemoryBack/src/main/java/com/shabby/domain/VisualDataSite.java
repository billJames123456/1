package com.shabby.domain;

public class VisualDataSite {
    private String imageSite;
    private Integer number;
    public VisualDataSite(){}
    public VisualDataSite(String imageSite, Integer number) {
        this.imageSite = imageSite;
        this.number = number;
    }

    public String getImageSite() {
        return imageSite;
    }

    public void setImageSite(String imageSite) {
        this.imageSite = imageSite;
    }

    public Integer getNumber() {
        return number;
    }

    public void setNumber(Integer number) {
        this.number = number;
    }

    @Override
    public String toString() {
        return "VisualDataSite{" +
                "imageSite='" + imageSite + '\'' +
                ", number=" + number +
                '}';
    }
}
