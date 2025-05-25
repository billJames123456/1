package com.shabby.controller;

import com.shabby.utils.RedisUtil;
import com.shabby.utils.SendEmailUtil;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;


@RestController
public class SendEmailController {
    @Resource
    RedisUtil redisUtil;
    @Value("${spring.mail.code.time}")
    private int validTime;
    @Resource
    private SendEmailUtil se;
    @RequestMapping("/code")
    public String sendCode(@RequestParam("email")String email){
        System.out.println(email);
        String code = se.sendEmail(email);
        redisUtil.set(email,code);
        System.out.println(email+":"+code);
        return "Success";
    }
}
