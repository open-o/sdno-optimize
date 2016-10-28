/*
Navicat MySQL Data Transfer

Source Server         : 236
Source Server Version : 50631
Source Host           : 219.141.189.236:3306
Source Database       : tunnel

Target Server Type    : MYSQL
Target Server Version : 50631
File Encoding         : 65001

Date: 2016-10-26 16:54:52
*/

SET FOREIGN_KEY_CHECKS=0;

-- ----------------------------
-- Table structure for `t_assigned_flow`
-- ----------------------------
DROP TABLE IF EXISTS `t_assigned_flow`;
CREATE TABLE `t_assigned_flow` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `lsp_id` int(10) unsigned NOT NULL,
  `netip` int(11) unsigned DEFAULT NULL COMMENT 'source ip',
  `netip_str` varchar(16) DEFAULT NULL,
  `mask_bit` tinyint(3) unsigned DEFAULT NULL,
  `mask_int` int(11) unsigned DEFAULT NULL,
  `customer_id` int(10) DEFAULT NULL,
  `customer_name` varchar(32) DEFAULT NULL,
  `status` tinyint(4) DEFAULT NULL COMMENT 'The flow status: Not Scheduled(-1), scheduling(0), scheduled(1), De-scheduling(2)',
  `user_data` varchar(16384) DEFAULT NULL,
  `flow_id` int(10) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `lsp_id1` (`lsp_id`) USING BTREE,
  CONSTRAINT `t_lsp_ibfk_1` FOREIGN KEY (`lsp_id`) REFERENCES `t_lsp` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of t_assigned_flow
-- ----------------------------

-- ----------------------------
-- Table structure for `t_lsp`
-- ----------------------------
DROP TABLE IF EXISTS `t_lsp`;
CREATE TABLE `t_lsp` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(45) DEFAULT NULL,
  `from_router_id` varchar(16) DEFAULT NULL,
  `from_router_ip` varchar(16) DEFAULT NULL,
  `from_port_id` varchar(16) DEFAULT NULL,
  `to_router_id` varchar(16) DEFAULT NULL,
  `to_router_ip` varchar(16) DEFAULT NULL,
  `to_port_id` varchar(16) DEFAULT NULL,
  `bandwidth` float DEFAULT NULL COMMENT '带宽，Mbps',
  `delay` float DEFAULT NULL COMMENT '时延, ms',
  `priority` tinyint(4) DEFAULT NULL,
  `control_type` tinyint(4) DEFAULT NULL COMMENT '0: delegated; 1: owner',
  `path_type` tinyint(4) DEFAULT NULL COMMENT '0, standby; 1: primary; 2, secondary',
  `status` tinyint(4) DEFAULT NULL COMMENT 'The status of lsp: creating(0), up(1), down(-1), missing(-2), deleting(2), deleted(3)',
  `user_data` varchar(8192) DEFAULT NULL,
  `hop_list` varchar(4096) DEFAULT NULL COMMENT 'hopes mulst be in the path ',
  `path` varchar(8192) DEFAULT NULL COMMENT 'actual path of lsp',
  PRIMARY KEY (`id`),
  KEY `from_router_id1` (`from_router_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=167 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of t_lsp
-- ----------------------------
INSERT INTO `t_lsp` VALUES ('157', 'BJ-WH-NJ-SH', '9', '', '', '10', '', '', '4000', null, null, null, null, '3', '{}', '9,11,12,10', '9,10');
INSERT INTO `t_lsp` VALUES ('158', 'BJ-SH', '9', '', '', '10', '', '', '1000', null, null, null, null, '3', '{}', '9,11,12,10', '9,10');
INSERT INTO `t_lsp` VALUES ('159', '123', '1', '', '', '5', '', '', '1000', null, null, null, null, '3', '{}', '1,5', '1,5');
INSERT INTO `t_lsp` VALUES ('160', '1234', '9', '', '', '10', '', '', '500', null, null, null, null, '3', '{}', '9,11,12,10', '9,10');
INSERT INTO `t_lsp` VALUES ('161', '123', '1', '', '', '5', '', '', '1000', null, null, null, null, '3', '{}', '1,5', '1,5');
INSERT INTO `t_lsp` VALUES ('163', 'test1', '1', '', '', '5', '', '', '1000', null, null, null, null, '3', '{}', '1,2,9,10,6,5', '1,5');
INSERT INTO `t_lsp` VALUES ('164', '123', '9', '', '', '10', '', '', '1000', null, null, null, null, '3', '{}', '9,11,12,10', '9,10');
INSERT INTO `t_lsp` VALUES ('165', '222', '1', '', '', '5', '', '', '1000', null, null, null, null, '3', '{}', '1,5', '1,5');
INSERT INTO `t_lsp` VALUES ('166', 'test-123', '1', '', '', '5', '', '', '1000', null, null, null, null, '3', '{}', '1,5', '1,5');
