package com.shabby.domain.VO;



public class AIResultVO {
    private Float confidence;
    private String value;

    @Override
    public String toString() {
        return "AIResultVO{" +
                "confidence=" + confidence +
                ", value='" + value + '\'' +
                '}';
    }

    public float getConfidence() {
        return confidence;
    }

    public void setConfidence(Float confidence) {
        this.confidence = confidence;
    }

    public String getValue() {
        return value;
    }

    public void setValue(String value) {
        this.value = value;
    }

    public AIResultVO(){}
    public AIResultVO(Float confidence, String value) {
        this.confidence = confidence;
        this.value = value;
    }
}
